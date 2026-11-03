"""掃描 MPU6050 CSV 的時間斷點，將 Markdown 表格印到終端機。"""
import argparse
import csv
import math
from pathlib import Path
import re
import sys
from datetime import datetime, time, timedelta


def filename_datetime(path):
    match = re.search(r'_(\d{12})(?:_\d+)?$', path.stem)
    if match:
        try:
            return datetime.strptime(match[1], '%y%m%d%H%M%S')
        except ValueError:
            pass
    return None


def scan(folder, threshold_ms):
    events = []
    files = rows = invalid = skipped = 0
    previous = None
    first_time = last_time = None
    paths = sorted(folder.glob('*.csv'), key=lambda p: (
        filename_datetime(p) or datetime.max, p.name))
    for path in paths:
        base = filename_datetime(path)
        day = base.date() if base else None
        previous_clock = None
        file_previous = None
        file_rows = 0
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.reader(stream)
            header = next(reader, [])
            if 'time' not in header:
                print(f'略過 {path.name}：沒有 time 欄位', file=sys.stderr)
                skipped += 1
                previous = None
                continue
            column = header.index('time')
            files += 1
            for row in reader:
                line = reader.line_num
                if not row:
                    continue
                try:
                    text = row[column].strip()
                    if 'T' in text or ' ' in text:
                        timestamp = datetime.fromisoformat(text)
                        if timestamp.tzinfo is not None:
                            raise ValueError('不支援含時區的時間')
                        day = timestamp.date()
                    else:
                        clock = time.fromisoformat(text)
                        if clock.tzinfo is not None or day is None:
                            raise ValueError('只有時分秒時，檔名需含 _YYMMDDhhmmss')
                        # 大於半天的倒退視為跨午夜，小幅倒退另外列為異常。
                        if previous_clock is not None:
                            delta = (datetime.combine(day, clock) -
                                     datetime.combine(day, previous_clock)).total_seconds()
                            if delta < -12 * 3600:
                                day += timedelta(days=1)
                        timestamp = datetime.combine(day, clock)
                    previous_clock = timestamp.time()
                except (ValueError, IndexError) as exc:
                    invalid += 1
                    if invalid <= 10:
                        print(f'時間無法解析 {path.name}:{line}：{exc}', file=sys.stderr)
                    # 無法解析的行不作為時間比較基準。
                    continue
                current = (timestamp, path, line)
                prior = file_previous or previous
                if prior is not None:
                    gap_ms = (timestamp - prior[0]).total_seconds() * 1000
                    kind = '跨檔斷點' if prior[1] != path else '檔內斷點'
                    if gap_ms < 0:
                        kind = '跨檔時間倒退' if prior[1] != path else '時間倒退'
                    elif gap_ms == 0:
                        kind = '相同時間戳'
                    if gap_ms > threshold_ms or gap_ms <= 0:
                        events.append((kind, prior, current, gap_ms))
                file_previous = current
                first_time = timestamp if first_time is None else min(first_time, timestamp)
                last_time = timestamp if last_time is None else max(last_time, timestamp)
                file_rows += 1
        rows += file_rows
        # 空檔不切斷有效資料的交界檢查。
        if file_previous is not None:
            previous = file_previous
    return events, files, rows, invalid, skipped, first_time, last_time


def report(folder, threshold_ms, result):
    events, files, rows, invalid, skipped, first, last = result
    gaps = [event for event in events if event[3] > threshold_ms]
    internal = sum(event[0] == '檔內斷點' for event in gaps)
    lines = ['# CSV 時間斷點檢查', '', f'掃描資料夾：{folder}', '',
             f'- 已檢查 {files} 個 CSV、{rows:,} 筆有效時間資料；略過 {skipped} 個檔案。',
             f'- 時間解析失敗：{invalid} 筆；這些行未參與比較。',
             f'- 判定門檻：相鄰時間差嚴格大於 {threshold_ms:g} 毫秒。',
             '- 只有時分秒的資料，日期由檔名推定；倒退超過 12 小時視為跨午夜。']
    if first is not None:
        lines.append(f'- 資料範圍：{first.isoformat(sep=" ", timespec="milliseconds")} ～ '
                     f'{last.isoformat(sep=" ", timespec="milliseconds")}')
    lines += [f'- 斷點 {len(gaps)} 處：檔內 {internal} 處、跨檔 {len(gaps)-internal} 處。',
              f'- 時間倒退 {sum(e[3] < 0 for e in events)} 處；相同時間戳 {sum(e[3] == 0 for e in events)} 處。']
    if gaps:
        lengths = [e[3] / 1000 for e in gaps]
        lines.append(f'- 斷點間隔：最短 {min(lengths):.3f} 秒、平均 {sum(lengths)/len(lengths):.3f} 秒、最長 {max(lengths):.3f} 秒。')
    lines += ['', '| # | 類型 | 斷點前日期時間 | 恢復日期時間 | 間隔（秒） | 前一筆檔案：行號 | 檔案：恢復資料行號 |',
              '|---:|---|---|---|---:|---|---|']
    for number, (kind, prior, current, ms) in enumerate(events, 1):
        lines.append(f'| {number} | {kind} | {prior[0].isoformat(sep=" ", timespec="milliseconds")} | '
                     f'{current[0].isoformat(sep=" ", timespec="milliseconds")} | {ms/1000:.3f} | '
                     f'{prior[1].name}:{prior[2]} | {current[1].name}:{current[2]} |')
    if not events:
        lines.append('未發現超過門檻的斷點、時間倒退或相同時間戳。' if rows else '沒有可檢查的資料。')
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', nargs='?', type=Path, default=Path(__file__).resolve().parent / 'data',
                        help='CSV 資料夾；預設為程式旁的 data，不掃描子資料夾')
    parser.add_argument('--threshold-ms', type=float, default=50, help='斷點門檻，預設 50 毫秒')
    parser.add_argument('--output', type=Path, help='另外儲存一份 Markdown 報告')
    args = parser.parse_args()
    if not args.folder.is_dir():
        parser.error(f'資料夾不存在：{args.folder}')
    if not math.isfinite(args.threshold_ms) or args.threshold_ms <= 0:
        parser.error('--threshold-ms 必須為有限正數')
    folder = args.folder.resolve()
    output = args.output.resolve() if args.output else None
    if output is not None and (output.suffix.lower() != '.md' or output.exists()):
        parser.error('--output 請指定尚未存在的 .md 檔案')
    text = report(folder, args.threshold_ms, scan(folder, args.threshold_ms))
    print(text)
    if output is not None:
        with output.open('x', encoding='utf-8') as stream:
            stream.write(text)

if __name__ == '__main__':
    main()
    input("done....")

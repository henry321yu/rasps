"""直接讀取雙 MPU6050 並存 CSV；不依賴 HTTP 或原本三支程式。"""
import argparse
import csv
import logging
import math
from pathlib import Path
import signal
import struct
import time
from datetime import datetime

ADDRESSES = (0x68, 0x69)
HEADER = ['time', 'ax1', 'ay1', 'az1', 'ax2', 'ay2', 'az2']


def prepare_sensors(bus):
    scales = []
    for address in ADDRESSES:
        power = bus.read_byte_data(address, 0x6B)
        if power & 0x40:
            # 僅喚醒睡眠中的裝置，不重設量程、濾波器或採樣設定。
            bus.write_byte_data(address, 0x6B, power & ~0x40)
            time.sleep(0.1)
        config = bus.read_byte_data(address, 0x1C)
        scales.append((16384.0, 8192.0, 4096.0, 2048.0)[(config >> 3) & 3])
    return scales


def read_acc(bus, address, scale):
    # 單次 SMBus block 交易包含暫存器位址及六個資料位元組。
    data = bus.read_i2c_block_data(address, 0x3B, 6)
    return tuple(value / scale for value in struct.unpack('>hhh', bytes(data)))


class CsvRecorder:
    def __init__(self, directory, rotation_seconds):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.rotation_seconds = rotation_seconds
        self.file = None
        self.deadline = 0
        self.flush_deadline = 0

    def write(self, timestamp, values):
        now = time.monotonic()
        if self.file is None or now >= self.deadline:
            self.close()
            stem = f'Dual_MPU6050_{datetime.now():%y%m%d%H%M%S}'
            suffix = 0
            while True:
                name = stem + (f'_{suffix}' if suffix else '') + '.csv'
                path = self.directory / name
                try:
                    self.file = path.open('x', newline='', encoding='utf-8')
                    break
                except FileExistsError:
                    suffix += 1
            self.writer = csv.writer(self.file)
            self.writer.writerow(HEADER)
            self.deadline = now + self.rotation_seconds
            self.flush_deadline = now
            logging.info('記錄檔案: %s', path)
        self.writer.writerow([timestamp.strftime('%H:%M:%S.%f')[:-3]] +
                             [f'{value:.6f}' for value in values])
        # 降低磁碟操作頻率；正常停止及切檔也會 flush。
        if now >= self.flush_deadline:
            self.file.flush()
            self.flush_deadline = now + 1

    def close(self):
        if self.file is not None:
            self.file.close()
            self.file = None


def positive_number(text):
    value = float(text)
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError('必須是有限正數')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hz', type=positive_number, default=100, help='目標讀取頻率，預設 100 Hz')
    parser.add_argument('--minutes', type=positive_number, default=10, help='切檔間隔，預設 30 分鐘')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent / 'stepper',
                        help='輸出目錄，預設為程式旁的 stepper')
    args = parser.parse_args()
    from smbus2 import SMBus

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    stopping = False

    def stop(signum, frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    recorder = CsvRecorder(args.output, args.minutes * 60)
    interval = 1 / args.hz
    total = errors = late = 0
    scales = None
    last_warning = -float('inf')
    last_status = deadline = time.monotonic()
    previous_sample = None
    batch_count = 0
    try:
        with SMBus(1) as bus:
            while not stopping:
                try:
                    if scales is None:
                        scales = prepare_sensors(bus)
                        deadline = time.monotonic()
                    values = tuple(value for address, scale in zip(ADDRESSES, scales)
                                   for value in read_acc(bus, address, scale))
                except OSError as exc:
                    errors += 1
                    now = time.monotonic()
                    if now - last_warning >= 5:
                        logging.warning('I2C 讀取失敗，累計 %d 次: %s', errors, exc)
                        last_warning = now
                    time.sleep(max(interval, 0.1))
                    deadline = time.monotonic()
                    continue

                sampled = time.monotonic()
                timestamp = datetime.now()
                if previous_sample is not None and sampled - previous_sample > max(0.05, interval * 2):
                    late += 1
                previous_sample = sampled
                # 不過濾相同值，不補造缺失樣本；兩顆感測器依序讀取。
                recorder.write(timestamp, values)
                total += 1
                batch_count += 1
                now = time.monotonic()
                if now - last_status >= 10:
                    logging.info('已寫入 %d 筆 | %.1f Hz | I2C 失敗 %d 次 | 長間隔 %d 次',
                                 total, batch_count / (now - last_status), errors, late)
                    last_status, batch_count = now, 0
                deadline += interval
                if deadline < now:
                    deadline = now + interval
                time.sleep(max(0, deadline - time.monotonic()))
    finally:
        recorder.close()
        logging.info('記錄結束，共 %d 筆，I2C 失敗 %d 次，長間隔 %d 次', total, errors, late)


if __name__ == '__main__':
    main()

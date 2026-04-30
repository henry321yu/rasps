import os
import re
import glob
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import matplotlib.dates as mdates
import time

# =========================
# 資料夾路徑
# =========================
folder = ''  # 設定你的資料夾路徑

smoothk = 1
plot_delay = 5
last_datas = 999999

plt.rcParams['font.family'] = 'Microsoft JhengHei'
plt.ion()
fig, ax = plt.subplots()

# 👉 新增：記錄檔案大小，避免重複讀
last_size = {}

while True:
    all_dfs = []

    file_list = sorted(glob.glob(os.path.join(folder, 'humi_log_*.txt')))

    for filepath in file_list:
        filename = os.path.basename(filepath)

        match = re.match(r'humi_log_(\d{12})\.txt', filename)
        if not match:
            print(f'忽略檔案：{filename}')
            continue

        # =========================
        # 👉 檢查檔案是否有更新（避免重讀）
        # =========================
        try:
            current_size = os.path.getsize(filepath)
        except Exception as e:
            print(f'⚠️ 讀取檔案大小失敗 {filename}：{e}')
            continue

        if filepath in last_size and current_size == last_size[filepath]:
            continue  # 沒變就跳過

        last_size[filepath] = current_size

        print(f'讀取：{filename}')

        try:
            # =========================
            # 👉 高效讀取（取代 iterrows）
            # =========================
            df = pd.read_csv(
                filepath,
                names=['datetime', 'device', 'temperature', 'humidity']
            )

            df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
            df = df.dropna()

        except Exception as e:
            print(f'⚠️ 讀取失敗 {filename}：{e}')
            continue

        if df.empty:
            continue

        all_dfs.append(df)

    if not all_dfs:
        print('⚠️ 無新資料，等待更新...')

        # 👉 關鍵：維持 matplotlib GUI 不凍結
        plt.pause(plot_delay)

        continue

    # =========================
    # 建 DataFrame
    # =========================
    T_all = pd.concat(all_dfs, ignore_index=True)
    T_all = T_all.sort_values(by='datetime')

    ax.clear()

    devices = T_all['device'].unique()

    for dev in devices:
        df_dev = T_all[T_all['device'] == dev].sort_values('datetime')

        # 👉 避免畫太多點造成卡頓
        df_dev = df_dev.tail(last_datas)

        x = df_dev['datetime']

        y_temp = df_dev['temperature'].rolling(smoothk, min_periods=1).mean()
        y_humi = df_dev['humidity'].rolling(smoothk, min_periods=1).mean()

        ax.plot(x, y_temp, marker='.', linestyle='None', markersize=2, label=f'DEV{dev} Temp')
        ax.plot(x, y_humi, marker='.', linestyle='None', markersize=2, label=f'DEV{dev} Humi')

        # 最新值標記（含名稱）
        ax.plot(x.iloc[-1], y_temp.iloc[-1], 'o')
        ax.text(
            x.iloc[-1],
            y_temp.iloc[-1],
            f'DEV{int(dev)} Temp: {y_temp.iloc[-1]:.2f}',
            fontsize=8
        )

        ax.plot(x.iloc[-1], y_humi.iloc[-1], 'o')
        ax.text(
            x.iloc[-1],
            y_humi.iloc[-1],
            f'DEV{int(dev)} Humi: {y_humi.iloc[-1]:.2f}',
            fontsize=8
        )

        print(f'DEV{dev} 溫度: {y_temp.iloc[-1]:.2f}, 濕度: {y_humi.iloc[-1]:.2f}')

    # =========================
    # 圖表設定
    # =========================
    ax.set_title(f'{T_all["datetime"].iloc[0].strftime("%Y-%m-%d %H:%M:%S")} ~ {T_all["datetime"].iloc[-1].strftime("%Y-%m-%d %H:%M:%S")}')
    ax.set_xlabel('Time')
    ax.set_ylabel('Value')
    ax.grid(True)
    ax.legend()

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M:%S'))
    fig.autofmt_xdate()

    plt.draw()
    print(f"✅ 更新完成：{datetime.now().strftime('%H:%M:%S')}")
    plt.pause(plot_delay)
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

plt.rcParams['font.family'] = 'Microsoft JhengHei'
plt.ion()
fig, ax = plt.subplots()

while True:
    all_rows = []

    file_list = sorted(glob.glob(os.path.join(folder, 'humi_log_*.txt')))

    for filepath in file_list:
        filename = os.path.basename(filepath)

        match = re.match(r'humi_log_(\d{12})\.txt', filename)
        if not match:
            print(f'忽略檔案：{filename}')
            continue

        print(f'讀取：{filename}')

        try:
            df = pd.read_csv(filepath, header=None)
        except Exception as e:
            print(f'⚠️ 讀取失敗 {filename}：{e}')
            continue

        if df.empty:
            continue

        # =========================
        # 每一列處理
        # =========================
        for _, row in df.iterrows():
            try:
                dt = pd.to_datetime(row.iloc[0], errors='coerce')
                if pd.isna(dt):
                    continue

                values = row.iloc[1:].values

                # 每 3 個一組: (id, temp, humi)
                for i in range(0, len(values), 3):
                    if i + 2 >= len(values):
                        break

                    device_id = values[i]
                    temp = pd.to_numeric(values[i + 1], errors='coerce')
                    humi = pd.to_numeric(values[i + 2], errors='coerce')

                    if pd.isna(temp) or pd.isna(humi):
                        continue

                    all_rows.append([dt, int(device_id), temp, humi])

            except Exception as e:
                print(f'⚠️ row error: {e}')

    if not all_rows:
        print('⚠️ 無資料，5 秒後重試')
        time.sleep(5)
        continue

    # =========================
    # 建 DataFrame
    # =========================
    T_all = pd.DataFrame(all_rows, columns=['datetime', 'device', 'temperature', 'humidity'])
    T_all = T_all.sort_values(by='datetime')

    ax.clear()

    devices = T_all['device'].unique()

    for dev in devices:
        df_dev = T_all[T_all['device'] == dev].sort_values('datetime')

        x = df_dev['datetime']

        y_temp = df_dev['temperature'].rolling(smoothk, min_periods=1).mean()
        y_humi = df_dev['humidity'].rolling(smoothk, min_periods=1).mean()

        ax.plot(x, y_temp, marker='.', linestyle='None', markersize=2, label=f'DEV{dev} Temp')
        ax.plot(x, y_humi, marker='.', linestyle='None', markersize=2, label=f'DEV{dev} Humi')

        # 最新值標記
        ax.plot(x.iloc[-1], y_temp.iloc[-1], 'o')
        ax.text(x.iloc[-1], y_temp.iloc[-1], f'{y_temp.iloc[-1]:.2f}')

        ax.plot(x.iloc[-1], y_humi.iloc[-1], 'o')
        ax.text(x.iloc[-1], y_humi.iloc[-1], f'{y_humi.iloc[-1]:.2f}')

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
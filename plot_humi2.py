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

smoothk = 10

plt.rcParams['font.family'] = 'Microsoft JhengHei'
plt.ion()
fig, ax = plt.subplots()

while True:
    T_all = pd.DataFrame()

    file_list = sorted(glob.glob(os.path.join(folder, 'humi_*.txt')))

    for filepath in file_list:
        filename = os.path.basename(filepath)

        # 解析檔名時間 YYMMDDHHMMSS
        match = re.match(r'humi_(\d{12})\.txt', filename)
        if not match:
            print(f'忽略檔案：{filename}')
            continue

        print(f'讀取：{filename}')

        try:
            # 讀取無標題 CSV, 新格式: datetime, temperature, humidity
            T = pd.read_csv(filepath, header=None, names=['datetime', 'temperature', 'humidity'])
        except Exception as e:
            print(f'⚠️ 無法讀取 {filename}，錯誤：{e}')
            continue

        if T.empty:
            print(f'⚠️ 檔案 {filename} 沒有資料')
            continue

        # 解析時間
        T['datetime'] = pd.to_datetime(T['datetime'], format='%Y-%m-%d %H:%M:%S.%f', errors='coerce')
        T['temperature'] = pd.to_numeric(T['temperature'], errors='coerce')
        T['humidity'] = pd.to_numeric(T['humidity'], errors='coerce')

        # 清掉錯誤資料
        T = T.dropna()

        T_all = pd.concat([T_all, T], ignore_index=True)

    if T_all.empty:
        print('⚠️ 沒有讀取到任何資料，5 秒後重試')
        time.sleep(5)
        continue

    # =========================
    # 排序時間
    # =========================
    T_all = T_all.sort_values(by='datetime')

    x = T_all['datetime']
    y_temp = T_all['temperature']
    y_humi = T_all['humidity']

    # 平滑
    y_temp_smooth = y_temp.rolling(smoothk, min_periods=1).mean()
    y_humi_smooth = y_humi.rolling(smoothk, min_periods=1).mean()

    x_1 = x.iloc[-1]
    temp_end = y_temp_smooth.iloc[-1]
    humi_end = y_humi_smooth.iloc[-1]

    # =========================
    # 畫圖
    # =========================
    ax.clear()

    ax.plot(x, y_temp_smooth, color='red', marker='.', linestyle='None', markersize=1, label='Temperature')
    ax.plot(x, y_humi_smooth, color='blue', marker='.', linestyle='None', markersize=1, label='Humidity')

    ax.plot(x_1, temp_end, 'ro')
    ax.text(x_1, temp_end, f'{temp_end:.2f}', fontsize=10, color='red', verticalalignment='bottom')

    ax.plot(x_1, humi_end, 'bo')
    ax.text(x_1, humi_end, f'{humi_end:.2f}', fontsize=10, color='blue', verticalalignment='bottom')

    print(f'目前溫度: {temp_end:.2f}, 濕度: {humi_end:.2f}')

    ax.set_title(f'{x.iloc[0].strftime("%Y-%m-%d %H:%M:%S")} ~ {x_1.strftime("%Y-%m-%d %H:%M:%S")}')
    ax.set_xlabel('Time')
    ax.set_ylabel('Value')
    ax.grid(True)
    ax.legend()

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M:%S'))
    fig.autofmt_xdate()

    plt.draw()
    print(f"✅ 圖表更新完成：{datetime.now().strftime('%H:%M:%S')}")
    plt.pause(10)
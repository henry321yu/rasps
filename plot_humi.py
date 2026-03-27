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

    file_list = sorted(glob.glob(os.path.join(folder, 'humi_log_*.txt')))

    for filepath in file_list:
        filename = os.path.basename(filepath)

        # 解析檔名時間 YYMMDDHHMMSS
        match = re.match(r'humi_log_(\d{12})\.txt', filename)
        if not match:
            print(f'忽略檔案：{filename}')
            continue

        print(f'讀取：{filename}')

        try:
            # 讀取無標題 CSV
            T = pd.read_csv(filepath, header=None, names=['datetime', 'humidity'])
        except Exception as e:
            print(f'⚠️ 無法讀取 {filename}，錯誤：{e}')
            continue

        if T.empty:
            print(f'⚠️ 檔案 {filename} 沒有資料')
            continue

        # 解析時間
        T['datetime'] = pd.to_datetime(T['datetime'], errors='coerce')
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
    y = T_all['humidity']


    # 平滑
    y_smooth = y.rolling(smoothk, min_periods=1).mean()

    x_0 = x.iloc[0]
    x_1 = x.iloc[-1]
    y_end = y_smooth.iloc[-1]

    # =========================
    # 畫圖
    # =========================
    ax.clear()

    ax.plot(x, y_smooth, marker='.', linestyle='None', markersize=1, label='Humidity')
    ax.plot(x_1, y_end, 'o')

    ax.text(x_1, y_end, f'{y_end:.2f}', fontsize=10)

    print(f'目前濕度: {y_end:.3f}')

    ax.set_title(f'{x_0.strftime("%Y-%m-%d %H:%M:%S")} ~ {x_1.strftime("%Y-%m-%d %H:%M:%S")}')
    ax.set_xlabel('Time')
    ax.set_ylabel('Humidity')
    ax.grid(True)
    ax.legend()

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M:%S'))
    fig.autofmt_xdate()

    plt.draw()

    print(f"✅ 圖表更新完成：{datetime.now().strftime('%H:%M:%S')}")
    plt.pause(10)
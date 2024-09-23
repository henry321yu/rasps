import configparser
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from pyproj import Transformer
import numpy as np

# 確認 datapath.ini 是否存在，若不存在則生成
if not os.path.exists('datapath.ini'):
    print("datapath.ini 不存在，正在創建...")
    config = configparser.ConfigParser()
    config['Paths'] = {'folder_path':'請輸入資料夾路徑'}
    
    with open('datapath.ini', 'w') as configfile:
        config.write(configfile)
    print("datapath.ini 已生成，請開啟並設置資料夾路徑。")
    sleep(3)
    exit()

# 讀取INI檔案
config = configparser.ConfigParser()
config.read('datapath.ini')

# 確認資料夾路徑是否已設置
folder_path = config['Paths']['folder_path']
if folder_path == '請輸入資料夾路徑':
    print("請先在 datapath.ini 中設置資料夾路徑。")
    sleep(3)
    exit()

# 初始化一個空的 DataFrame 來儲存所有的資料
all_data = pd.DataFrame()

# TWD97 (EPSG:3826) 投影系統
transformer = Transformer.from_crs("EPSG:4326", "EPSG:3826")

# 用來儲存顏色的字典
color_map = {}

print("Reading data...")

# 遍歷資料夾中的所有.txt檔案
for filename in os.listdir(folder_path):
    if filename.endswith(".txt"):
        file_path = os.path.join(folder_path, filename)
        print(f"Reading:{file_path}")
        
        # 提取日期
        date_str = filename.split('_')[1]  # 取得日期部分
        date = datetime.strptime(date_str, '%Y%m%d').date()
        
        # 隨機生成顏色或使用特定顏色
        if date not in color_map:
            color_map[date] = np.random.rand(3,)  # 隨機顏色

        # 初始化一個暫存列表來存儲數據
        temp_data = []
        
        # 打開檔案逐行讀取
        with open(file_path, 'r') as file:
            for line in file:
                if 'END_OF_FILE' in line:
                    break
                split_line = line.strip().split()
                if len(split_line) == 9:
                    split_line.extend(['0', '0'])  # 增加 'volt' 和 'current' 欄位為 0
                temp_data.append(split_line)

        if temp_data and len(temp_data) > 5:  # 檢查至少有5行數據
            data = pd.DataFrame(temp_data)
            data.columns = ['UTC+8', 'ax', 'ay', 'az', 'lat', 'lon', 'altitude', 'gps_mode', 'temperature', 'volt', 'current']
            data['UTC+8'] = pd.to_datetime(data['UTC+8'], format='%H:%M:%S.%f', errors='coerce')
            data = data.dropna(subset=['UTC+8'])
            for col in data.columns[1:]:
                data[col] = pd.to_numeric(data[col], errors='coerce')
            data = data.dropna()

            if len(data) > 0:
                twd97_x, twd97_y = transformer.transform(data['lat'].values, data['lon'].values)
                data['twd97_x'] = twd97_x
                data['twd97_y'] = twd97_y
                data['date'] = date
                all_data = pd.concat([all_data, data])

# 確保數據按時間順序排序
all_data.sort_values(by='UTC+8', inplace=True)
all_data = all_data[all_data['current'] != 0] #刪除 current為0


# 繪製圖表，根據日期使用不同顏色
plt.figure(figsize=(10, 6))

for date, color in color_map.items():
    date_data = all_data[all_data['date'] == date]
    plt.plot(date_data['UTC+8'], date_data['volt'], '.', label=str(date), color=color)

plt.ylim(10, 15)
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
plt.xlabel('Time (UTC+8)')
plt.ylabel('Volt')
plt.title('Volt vs Time')
plt.xticks(rotation=45)
plt.legend(title='Date')
plt.tight_layout()
plt.show(block=False)

# 繪製 current 圖表
plt.figure(figsize=(10, 6))

for date, color in color_map.items():
    date_data = all_data[all_data['date'] == date]
    plt.plot(date_data['UTC+8'], date_data['current'], '.', label=str(date), color=color)

plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
plt.xlabel('Time (UTC+8)')
plt.ylabel('Current')
plt.title('Current vs Time')
plt.xticks(rotation=45)
plt.legend(title='Date')
plt.tight_layout()
plt.show(block=False)

# 繪製 gps_mode 圖表
plt.figure(figsize=(10, 6))

for date, color in color_map.items():
    date_data = all_data[all_data['date'] == date]
    plt.plot(date_data['UTC+8'], date_data['gps_mode'], '.', label=str(date), color=color)

plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
plt.xlabel('Time (UTC+8)')
plt.ylabel('GPS Mode')
plt.title('GPS Mode vs Time')
plt.xticks(rotation=45)
plt.legend(title='Date')
plt.tight_layout()
plt.show(block=False)

# 繪製 temperature 圖表
plt.figure(figsize=(10, 6))

for date, color in color_map.items():
    date_data = all_data[all_data['date'] == date]
    plt.plot(date_data['UTC+8'], date_data['temperature'], '.', label=str(date), color=color)

plt.ylim(10, 60)
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
plt.xlabel('Time (UTC+8)')
plt.ylabel('Temperature')
plt.title('Temperature vs Time')
plt.xticks(rotation=45)
plt.legend(title='Date')
plt.tight_layout()
plt.show(block=False)

# 只選擇 gps_mode 為 4 的資料
gps_mode_4_data = all_data[all_data['gps_mode'] == 4]

# 繪製 twd97_x vs UTC+8 (僅限 gps_mode 為 4 的數據)
plt.figure(figsize=(10, 6))

for date, color in color_map.items():
    date_gps_data = gps_mode_4_data[gps_mode_4_data['date'] == date]
    plt.plot(date_gps_data['UTC+8'], date_gps_data['twd97_x'], '.', label=str(date), color=color)

plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
plt.xlabel('Time (UTC+8)')
plt.ylabel('TWD97 X')
plt.title('TWD97 X vs Time (GPS Mode=4)')
plt.xticks(rotation=45)
plt.legend(title='Date')
plt.tight_layout()
plt.show()

# 繪製 twd97_y vs UTC+8 (僅限 gps_mode 為 4 的數據)
plt.figure(figsize=(10, 6))

for date, color in color_map.items():
    date_gps_data = gps_mode_4_data[gps_mode_4_data['date'] == date]
    plt.plot(date_gps_data['UTC+8'], date_gps_data['twd97_y'], '.', label=str(date), color=color)

plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
plt.xlabel('Time (UTC+8)')
plt.ylabel('TWD97 Y')
plt.title('TWD97 Y vs Time (GPS Mode=4)')
plt.xticks(rotation=45)
plt.legend(title='Date')
plt.tight_layout()
plt.show()
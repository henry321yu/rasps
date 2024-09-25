import os
import configparser
# 確認 datapath.ini 是否存在，若不存在則生成
if not os.path.exists('datapath.ini'):
    print("datapath.ini 不存在，正在創建...")
    config = configparser.ConfigParser()
    config['Paths'] = {'folder_path':'請輸入資料夾路徑'}
    
    with open('datapath.ini', 'w') as configfile:
        config.write(configfile)
    print("datapath.ini 已生成，請開啟並設置資料夾路徑。")
    input("press enter to exit...")
    exit() 

# 讀取INI檔案
config = configparser.ConfigParser()

try:
    with open('datapath.ini', 'r', encoding='utf-8') as f:
        config.read_file(f)
except Exception as e:
    print(f"datapath.ini error: {e}")
    input("press enter to exit...")
    exit()
    

# 確認資料夾路徑是否已設置
folder_path = config['Paths']['folder_path']
if folder_path == '請輸入資料夾路徑':
    print("請先在 datapath.ini 中設置資料夾路徑。")
    input("press enter to exit...")
    exit()

print(f"datapath : {folder_path}")
print("importing library for running...")

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from pyproj import Transformer
import numpy as np

# 初始化一個空的 DataFrame 來儲存所有的資料
all_data = pd.DataFrame()

# TWD97 (EPSG:3826) 投影系統
transformer = Transformer.from_crs("EPSG:4326", "EPSG:3826")

# 用來儲存顏色的字典
color_map = {}
color_index = 0  # 用來追蹤顏色的索引

# 生成 100 個顏色
colors = []
num=[3,5,7] #設定隨機顏色參數
for j in range(100):
    r = ((j + num[0])% num[2]) / num[2]
    g = ((j + num[1]) % num[1]) / num[1]
    b = ((j + num[2]) % num[0]) / num[0]
    colors.append((r, g, b))
    
figuresize=[7,4]
plotsize=3

print("Reading all .txt files...")

try:
    # 遍歷資料夾中的所有.txt檔案
    for filename in os.listdir(folder_path):
        if filename.endswith(".txt"):
            file_path = os.path.join(folder_path, filename)
            print(f"loading : {file_path}")
            
            # 提取日期
            date_str = filename.split('_')[1]  # 取得日期部分
            date = datetime.strptime(date_str, '%Y%m%d').date()
            
            # 隨機生成顏色或使用特定顏色
            if date not in color_map:
                color_map[date] = colors[color_index % len(colors)]  # 隨機顏色
                color_index += 1

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

            if temp_data and len(temp_data) > 3:  # 檢查至少有3行數據
                data = pd.DataFrame(temp_data)
                data.columns = ['UTC+8', 'ax', 'ay', 'az', 'lat', 'lon', 'alt', 'gps_mode', 'temperature', 'volt', 'current']
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
except:
    print("error wrong path or files maybe...")
    input("press enter to exit...")
    exit()
    
# 確保數據按時間順序排序
try:
    all_data.sort_values(by='UTC+8', inplace=True)
except:
    print("error files maybe...")
    input("press enter to exit...")
    exit()
    
all_data = all_data[all_data['current'] != 0] #刪除 current為0

print("plotting...")


# 繪製圖表，根據日期使用不同顏色
# 繪製 Voltage 圖表
plt.figure(figsize=(figuresize[0], figuresize[1]))

for date, color in color_map.items():
    date_data = all_data[all_data['date'] == date]
    plt.plot(date_data['UTC+8'], date_data['volt'], '.', label=str(date), color=color, markersize=plotsize)

plt.ylim(10, 15)
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
plt.xlabel('Time(UTC+8)')
plt.ylabel('Voltage(V)')
plt.title('Voltage')
plt.xticks(rotation=45)
plt.legend(title='Date')
plt.tight_layout()
plt.show(block=False)

# 繪製 current 圖表
plt.figure(figsize=(figuresize[0], figuresize[1]))

for date, color in color_map.items():
    date_data = all_data[all_data['date'] == date]
    plt.plot(date_data['UTC+8'], date_data['current'], '.', label=str(date), color=color, markersize=plotsize)

plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
plt.xlabel('Time(UTC+8)')
plt.ylabel('Current(A)')
plt.title('Current')
plt.xticks(rotation=45)
plt.legend(title='Date')
plt.tight_layout()
plt.show(block=False)

# 繪製 temperature 圖表
plt.figure(figsize=(figuresize[0], figuresize[1]))

for date, color in color_map.items():
    date_data = all_data[all_data['date'] == date]
    plt.plot(date_data['UTC+8'], date_data['temperature'], '.', label=str(date), color=color, markersize=plotsize)

plt.ylim(10, 60)
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
plt.xlabel('Time (UTC+8)')
plt.ylabel('Temperature(C)')
plt.title('Temperature')
plt.xticks(rotation=45)
plt.legend(title='Date')
plt.tight_layout()
plt.show(block=False)

# 繪製 gps_mode 圖表
plt.figure(figsize=(figuresize[0], figuresize[1]))

for date, color in color_map.items():
    date_data = all_data[all_data['date'] == date]
    plt.plot(date_data['UTC+8'], date_data['gps_mode'], '.', label=str(date), color=color, markersize=plotsize)

plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
plt.xlabel('Time(UTC+8)')
plt.ylabel('GPS Mode')
plt.title('GPS Mode vs Time')
plt.xticks(rotation=45)
plt.legend(title='Date')
plt.tight_layout()
plt.show(block=False)

# 只選擇 gps_mode 為 4 的資料
gps_mode_4_data = all_data[all_data['gps_mode'] == 4]

# 繪製 twd97_x vs UTC+8 (僅限 gps_mode 為 4 的數據)
plt.figure(figsize=(figuresize[0], figuresize[1]))

for date, color in color_map.items():
    date_gps_data = gps_mode_4_data[gps_mode_4_data['date'] == date]
    plt.plot(date_gps_data['UTC+8'], date_gps_data['twd97_x'], '.', label=str(date), color=color, markersize=plotsize)

plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
plt.xlabel('Time(UTC+8)')
plt.ylabel('TWD97 X(m)')
plt.title('TWD97 X')
plt.xticks(rotation=45)
plt.legend(title='Date')
plt.tight_layout()
plt.show(block=False)

# 繪製 twd97_y vs UTC+8 (僅限 gps_mode 為 4 的數據)
plt.figure(figsize=(figuresize[0], figuresize[1]))

for date, color in color_map.items():
    date_gps_data = gps_mode_4_data[gps_mode_4_data['date'] == date]
    plt.plot(date_gps_data['UTC+8'], date_gps_data['twd97_y'], '.', label=str(date), color=color, markersize=plotsize)

plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
plt.xlabel('Time(UTC+8)')
plt.ylabel('TWD97 Y(m)')
plt.title('TWD97 Y')
plt.xticks(rotation=45)
plt.legend(title='Date')
plt.tight_layout()
plt.show(block=False)

# 繪製 altitude 圖表
plt.figure(figsize=(figuresize[0], figuresize[1]))

for date, color in color_map.items():
    date_gps_data = gps_mode_4_data[gps_mode_4_data['date'] == date]
    plt.plot(date_gps_data['UTC+8'], date_gps_data['alt'], '.', label=str(date), color=color, markersize=plotsize)

plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
plt.xlabel('Time(UTC+8)')
plt.ylabel('altitude(m)')
plt.title('altitude')
plt.xticks(rotation=45)
plt.legend(title='Date')
plt.tight_layout()
plt.show(block=False)

# 繪製 twd97_y vs twd97_y 圖表
plt.figure(figsize=(figuresize[0], figuresize[1]))

for date, color in color_map.items():
    date_gps_data = gps_mode_4_data[gps_mode_4_data['date'] == date]
    plt.plot(date_gps_data['twd97_x'], date_gps_data['twd97_y'], '.', label=str(date), color=color, markersize=plotsize)

plt.xlabel('TWD97 X(m)')
plt.ylabel('TWD97 Y(m)')
plt.title('TWD97 X vs TWD97 Y')
plt.legend(title='Date')
plt.tight_layout()
plt.show()

print("program completed...")  # 等待用戶按下 Enter
input("press enter to exit...")
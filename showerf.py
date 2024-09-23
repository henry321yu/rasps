import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from pyproj import Transformer
import numpy as np

# 定義資料夾路徑
# folder_path = r"C:\Users\sgrc-325\Desktop\py\rasp log"
folder_path = r"C:\Users\fly\GB_Sar_and_GPS\log"
# folder_path = r"C:\rasp log"

# 初始化一個空的 DataFrame 來儲存所有的資料
all_data = pd.DataFrame()

# TWD97 (EPSG:3826) 投影系統
transformer = Transformer.from_crs("EPSG:4326", "EPSG:3826")

# 用來儲存顏色的字典
color_map = {}

# 遍歷資料夾中的所有.txt檔案
for filename in os.listdir(folder_path):
    if filename.endswith(".txt"):
        file_path = os.path.join(folder_path, filename)
        
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
                # 如果遇到 'END_OF_FILE'，則跳出迴圈
                if 'END_OF_FILE' in line:
                    break
                
                # 將每行內容分割
                split_line = line.strip().split()
                
                # 檢查是否只有9個欄位，若是則補上'volt'和'current'為0
                if len(split_line) == 9:
                    split_line.extend(['0', '0'])  # 增加 'volt' 和 'current' 欄位為 0
                
                # 將結果存儲在 temp_data 中
                temp_data.append(split_line)

        # 如果有資料，則將其轉換為 DataFrame
        if temp_data and len(temp_data) > 5:  # 檢查至少有5行數據
            # 將暫存數據轉換為 DataFrame
            data = pd.DataFrame(temp_data)
            
            # 假設第1欄是時間，其他欄位為數據
            data.columns = ['UTC+8', 'ax', 'ay', 'az', 'lat', 'lon', 'altitude', 'gps_mode', 'temperature', 'volt', 'current']
            
            # 將時間欄轉換為datetime格式，並忽略不能解析的行
            data['UTC+8'] = pd.to_datetime(data['UTC+8'], format='%H:%M:%S.%f', errors='coerce')
            
            # 丟棄無法轉換時間的行
            data = data.dropna(subset=['UTC+8'])
            
            # 將所有除了'UTC+8'的欄位轉換為浮點數，無法轉換的值變為NaN
            for col in data.columns[1:]:
                data[col] = pd.to_numeric(data[col], errors='coerce')

            # 丟棄任何包含 NaN 的行
            data = data.dropna()

            # 檢查是否有足夠的數據
            if len(data) > 0:
                # 將 lat 和 lon 轉換為 TWD97 (EPSG:3826)
                twd97_x, twd97_y = transformer.transform(data['lat'].values, data['lon'].values)
                data['twd97_x'] = twd97_x
                data['twd97_y'] = twd97_y

                # 將日期與顏色新增到資料中
                data['date'] = date

                # 將資料彙整起來
                all_data = pd.concat([all_data, data])

# 確保數據按時間順序排序
all_data.sort_values(by='UTC+8', inplace=True)

# 繪製圖表，根據日期使用不同顏色
plt.figure(figsize=(10, 6))

for date, color in color_map.items():
    date_data = all_data[all_data['date'] == date]
    plt.plot(date_data['UTC+8'], date_data['volt'], '.', label=str(date), color=color)

plt.ylim(5, 20)
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



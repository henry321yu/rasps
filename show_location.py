import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from pyproj import Proj, Transformer

# 定義資料夾路徑
# folder_path = r"C:\Users\fly\GB_Sar_and_GPS\test20240922"
# folder_path = r"C:\Users\fly\GB_Sar_and_GPS\test"
folder_path = r"C:\Users\sgrc-325\Desktop\py\rasp log"

# 初始化一個空的 DataFrame 來儲存所有的資料
all_data = pd.DataFrame()

# TWD97 (EPSG:3826) 投影系統
transformer = Transformer.from_crs("EPSG:4326", "EPSG:3826")

# 遍歷資料夾中的所有.txt檔案
for filename in os.listdir(folder_path):
    if filename.endswith(".txt"):
        file_path = os.path.join(folder_path, filename)
        
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
        if temp_data:
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

            # 將 lat 和 lon 轉換為 TWD97 (EPSG:3826)
            twd97_x, twd97_y = transformer.transform(data['lat'].values, data['lon'].values)
            data['twd97_x'] = twd97_x
            data['twd97_y'] = twd97_y

            # 將資料彙整起來
            all_data = pd.concat([all_data, data])

# 確保數據按時間順序排序
all_data.sort_values(by='UTC+8', inplace=True)

# 繪製 volt 圖表
plt.figure(figsize=(10, 6))
plt.plot(all_data['UTC+8'], all_data['volt'], '.', label='volt')
plt.ylim(5,20)
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
plt.xlabel('Time (UTC+8)')
plt.ylabel('volt')
plt.title('volt vs UTC+8')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()


# 繪製 current 圖表
plt.figure(figsize=(10, 6))
plt.plot(all_data['UTC+8'], all_data['current'], '.', label='current')
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
plt.xlabel('Time (UTC+8)')
plt.ylabel('current')
plt.title('current vs UTC+8')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# 繪製 gps_mode 圖表
plt.figure(figsize=(10, 6))
plt.plot(all_data['UTC+8'], all_data['gps_mode'], '.', label='gps_mode')
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
plt.xlabel('Time (UTC+8)')
plt.ylabel('gps_mode')
plt.title('gps_mode vs UTC+8')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# 繪製 temperature 圖表
plt.figure(figsize=(10, 6))
plt.plot(all_data['UTC+8'], all_data['temperature'], '.', label='temperature')
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
plt.xlabel('Time (UTC+8)')
plt.ylabel('temperature')
plt.title('temperature vs UTC+8')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# 只選擇 gps_mode 為 4 的資料
gps_mode_4_data = all_data[all_data['gps_mode'] == 4]

# 繪製 twd97_x vs UTC+8 (僅限 gps_mode 為 4 的數據)
plt.figure(figsize=(10, 6))
plt.plot(gps_mode_4_data['UTC+8'], gps_mode_4_data['twd97_x'], '.', label='twd97_x (gps_mode=4)')
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
plt.xlabel('Time (UTC+8)')
plt.ylabel('twd97_x')
plt.title('twd97_x vs UTC+8 (gps_mode=4)')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# 繪製 twd97_y vs UTC+8 (僅限 gps_mode 為 4 的數據)
plt.figure(figsize=(10, 6))
plt.plot(gps_mode_4_data['UTC+8'], gps_mode_4_data['twd97_y'], '.', label='twd97_y (gps_mode=4)')
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
plt.xlabel('Time (UTC+8)')
plt.ylabel('twd97_y')
plt.title('twd97_y vs UTC+8 (gps_mode=4)')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# 檢查結果
print(all_data[['UTC+8', 'lat', 'lon', 'twd97_x', 'twd97_y', 'volt', 'current']].head())

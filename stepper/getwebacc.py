import requests
import time
import csv
import os
from datetime import datetime

# 替換成你的伺服器 IP
data_url = "http://26.107.7.251:6969/data?client_id=data_logger"

# 自動生成帶有日期時間的檔名 (例如: ADXL355_260716115110.csv)
time_string = datetime.now().strftime("%y%m%d%H%M%S")
csv_filename = f"ADXL355_{time_string}.csv"

# 紀錄已經抓取過的時間戳，避免重複儲存
seen_timestamps = set()

with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Time", "AX", "AY", "AZ", "Vector"])
    
    print(f"開始記錄數據至 {csv_filename} ... (按 Ctrl+C 停止)\n")
    
    try:
        while True:
            response = requests.get(data_url)
            if response.status_code == 200:
                data = response.json()
                
                # 如果沒有數據則略過
                if not data.get("t"):
                    time.sleep(0.5)
                    continue
                
                new_rows_count = 0
                latest_t = None
                
                # 遍歷抓取到的數據
                for i in range(len(data["t"])):
                    t = data["t"][i]
                    # 確保只寫入新的數據
                    if t not in seen_timestamps:
                        writer.writerow([
                            t, 
                            data["ax"][i], 
                            data["ay"][i], 
                            data["az"][i], 
                            data["vector"][i]
                        ])
                        seen_timestamps.add(t)
                        new_rows_count += 1
                        latest_t = t  # 記錄這批資料最新的時間軸
                        
                # 如果有寫入新資料，更新畫面資訊
                if new_rows_count > 0:
                    file.flush()  # 確保資料寫入硬碟，取得精準大小
                    file_size_bytes = os.path.getsize(csv_filename)
                    
                    # 根據大小自動轉換單位 (KB 或 MB)
                    if file_size_bytes < 1024 * 1024:
                        size_str = f"{file_size_bytes / 1024:.2f} KB"
                    else:
                        size_str = f"{file_size_bytes / (1024 * 1024):.2f} MB"
                        
                    print(f"{latest_t} | 本次寫入: {new_rows_count} 筆 | 檔案大小: {size_str}")
                        
            # 根據你的 DEFAULT_UPDATE_INTERVAL_MS 決定輪詢頻率 (預設 0.5 秒)
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n記錄結束。")
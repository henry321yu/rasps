import requests
import time
import csv
import os
from datetime import datetime, timedelta

# ================= 設定區 =================
SERVER_IP = "10.241.136.93"
CLIENT_ID = "data_logger"
DATA_URL = f"http://{SERVER_IP}:6969/data?client_id={CLIENT_ID}"

TARGET_HZ = 100      # 目標紀錄頻率
INTERVAL = 1000 / TARGET_HZ
TARGET_INTERVAL = timedelta(milliseconds=INTERVAL) 
# ==========================================

print("正在向 Server 配置 Logger 專屬設定...")
try:
    # 確保 Server 吐出最原始資料 (avg_n=1) 以及足夠的歷史長度避免漏接 (val=3000)
    requests.get(f"http://{SERVER_IP}:6969/set_average?client_id={CLIENT_ID}&val=1", timeout=3)
    requests.get(f"http://{SERVER_IP}:6969/set_display?client_id={CLIENT_ID}&val=3000", timeout=3)
    print("配置成功，準備開始記錄！\n")
except Exception as e:
    print(f"⚠️ 無法配置 Server (可能尚未啟動)，將使用預設值。原因: {e}\n")


time_string = datetime.now().strftime("%y%m%d%H%M%S")
csv_filename = f"Dual_MPU6050_{time_string}.csv"

seen_timestamps = set()
last_saved_time = None  # 紀錄上一筆寫入 CSV 的確切時間
last_calc_time = time.time() # [新增] 紀錄上次計算頻率的系統時間

with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["time", "ax1", "ay1", "az1", "ax2", "ay2", "az2"])
    
    print(f"開始記錄數據至 {csv_filename} ... (目標頻率: {TARGET_HZ}Hz, 按 Ctrl+C 停止)\n")
    
    try:
        while True:
            try:
                response = requests.get(DATA_URL, timeout=3)
            except requests.exceptions.RequestException:
                time.sleep(0.5)
                continue

            if response.status_code == 200:
                data = response.json()
                
                if not data.get("t"):
                    time.sleep(0.1)
                    continue
                
                new_rows_count = 0
                latest_t_str = None
                
                for i in range(len(data["t"])):
                    t_str = data["t"][i]
                    
                    # 若已看過該時間戳則直接跳過 (基礎去重)
                    if t_str in seen_timestamps:
                        continue
                    
                    # 解析時間 (HH:MM:SS.ms)
                    try:
                        current_time = datetime.strptime(t_str, "%H:%M:%S.%f")
                    except ValueError:
                        continue # 時間格式錯誤則略過
                    
                    should_save = False
                    
                    if last_saved_time is None:
                        should_save = True
                    else:
                        # 計算與上一筆寫入時間的間隔
                        delta = current_time - last_saved_time
                        
                        # 處理跨日問題 (23:59:59.999 跨越到 00:00:00.000)
                        if delta.days < 0:
                            delta += timedelta(days=1)
                        
                        # 只要時間間隔大於等於目標間隔，就允許儲存
                        if delta >= TARGET_INTERVAL:
                            should_save = True

                    if should_save:
                        writer.writerow([
                            t_str, 
                            f"{float(data['ax1'][i]):.6f}", 
                            f"{float(data['ay1'][i]):.6f}", 
                            f"{float(data['az1'][i]):.6f}", 
                            f"{float(data['ax2'][i]):.6f}", 
                            f"{float(data['ay2'][i]):.6f}", 
                            f"{float(data['az2'][i]):.6f}"
                        ])
                        last_saved_time = current_time
                        new_rows_count += 1
                        latest_t_str = t_str
                    
                    # 將時間加入已處理清單
                    seen_timestamps.add(t_str)
                    
                # 防止集合無限變大吃滿記憶體 (超過兩萬筆自動清理部分)
                if len(seen_timestamps) > 20000:
                    seen_timestamps.clear() 

                if new_rows_count > 0:
                    file.flush() 
                    file_size_bytes = os.path.getsize(csv_filename)
                    
                    if file_size_bytes < 1024 * 1024:
                        size_str = f"{file_size_bytes / 1024:.2f} KB"
                    else:
                        size_str = f"{file_size_bytes / (1024 * 1024):.2f} MB"
                    
                    # [新增] 計算實際頻率 (Hz)
                    now = time.time()
                    delta_sec = now - last_calc_time
                    current_hz = new_rows_count / delta_sec if delta_sec > 0 else 0
                    last_calc_time = now # 更新計算時間點
                    
                    # [修改] 將頻率加入 Print 輸出中
                    print(f"{latest_t_str} | 本次過濾寫入: {new_rows_count:3} 筆 | 目前頻率: {current_hz:5.1f} Hz | 檔案大小: {size_str}")
                        
            # 縮短索取間隔，確保不漏接伺服器 Buffer 內的資料
            time.sleep(0.2)
            
    except KeyboardInterrupt:
        print("\n記錄結束。")
import time
from datetime import datetime
import os

current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
print("current time :", current_datetime)
# log_folder = r'C:\Users\sgrc-325\Desktop\py\log'
# log_folder = r'C:\Users\弘銘\Desktop\WFH\git\log'
log_folder = r'/home/rasp3/Desktop/log'
log_filename = f'logger_P_{current_datetime}.csv'
log_filepath = os.path.join(log_folder, log_filename)

# 記錄資料到檔案
with open("temperature_log.csv", "a") as log_file:
    log_file.write("Time,Temperature (C)\n")  # 寫入表頭
    while True:
        # 讀取 CPU 溫度
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as temp_file:
            cpu_temp = int(temp_file.read()) / 1000
        
        # 取得當前時間
        current_time = datetime.now().strftime("%H:%M:%S")

        # 記錄時間與溫度
        log_file.write(f"{current_time},{cpu_temp}\n")
        print(f"Logged: {current_time} - {cpu_temp}°C")

        # 每秒更新一次
        time.sleep(1)

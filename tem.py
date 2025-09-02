import time
from datetime import datetime

def get_temp():
    # 讀取系統檔案
    with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
        temp = int(f.read()) / 1000.0
    return temp

print("按 Ctrl+C 停止監看溫度")
while True:
    temp = get_temp()
    print(f"{datetime.now().strftime('%H:%M:%S')} | CPU 溫度: {temp:.1f}°C")
    time.sleep(1)

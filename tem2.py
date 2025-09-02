import time
from datetime import datetime
import psutil  # pip install psutil

def get_temp():
    """讀取 CPU 溫度"""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = int(f.read()) / 1000.0
        return temp
    except FileNotFoundError:
        return None

print("按 Ctrl+C 停止監看溫度與使用率")

while True:
    temp = get_temp()
    cpu_usage = psutil.cpu_percent(interval=1)  # CPU 使用率 (%)

    timestamp = datetime.now().strftime('%H:%M:%S')

    if temp is not None:
        print(f"{timestamp} | CPU 使用率: {cpu_usage:.1f}% | CPU 溫度: {temp:.1f}°C")
    else:
        print(f"{timestamp} | 無法讀取 CPU 溫度 | CPU 使用率: {cpu_usage:.1f}%")

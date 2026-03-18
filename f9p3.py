import os
import serial
from pyubx2 import UBXReader
import time
from datetime import datetime, timedelta

# ===== 目標資料夾 =====
folder = "f9p"
os.makedirs(folder, exist_ok=True)  # 不存在就建立

# ===== 建立檔名，用程式啟動當前時間（UTC+8） =====
now = datetime.now() + timedelta(hours=8)
filename = os.path.join(folder, f"gnss_log_{now.strftime('%y%m%d%H%M%S')}.bin")
print(f"Logging to: {filename}")

# ===== 開啟 serial port =====
ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
ubr = UBXReader(ser)

start_time = time.time()

def interpret_gps_mode(fix_type):
    """將 UBX fixType 整數轉成可讀字串"""
    modes = {
        0: "No Fix",
        1: "GPS Fix",
        2: "DGPS Fix",
        3: "3D Fix",
        4: "RTK Fixed",
        5: "RTK Float",
        6: "Dead Reckoning",
    }
    return modes.get(fix_type, "Unknown")

with open(filename, 'ab') as f:
    while True:
        try:
            raw, parsed = ubr.read()

            if raw:
                f.write(raw)
                f.flush()

            if parsed and parsed.identity == "NAV-PVT":
                # ===== 計算 runtime 與檔案大小 =====
                elapsed = time.time() - start_time
                size_mb = f.tell() / (1024*1024)

                # ===== 取得 GNSS UTC+8 =====
                dt = datetime(parsed.year, parsed.month, parsed.day,
                              parsed.hour, parsed.min, parsed.second)
                local_time = dt + timedelta(hours=8)

                # ===== 取得精度（mm → m） =====
                hAcc = parsed.hAcc / 1000
                vAcc = parsed.vAcc / 1000
                
                # ===== FixType 轉成字串 =====
                fix_str = interpret_gps_mode(parsed.fixType)

                print(f"""
Uptime: {elapsed:.1f} sec
File size: {size_mb:.2f} MB

Time (UTC+8): {local_time}
FixType: {fix_str}
Satellites: {parsed.numSV}

Horizontal Accuracy: {hAcc:.3f} m
Vertical Accuracy: {vAcc:.3f} m
""")

        except Exception as e:
            print("Error:", e)
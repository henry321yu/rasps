import serial
import pynmea2
import time   
from datetime import datetime, timedelta

# 👉 檔名時間
start_dt = datetime.now()
filename = f"gnss_log_{start_dt.strftime('%y%m%d%H%M%S')}.bin"

print(f"Logging to: {filename}")

# 👉 runtime 起始
start_time = time.time()

ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)

with open(filename, 'ab') as f:
    while True:
        try:
            line = ser.readline()
            if not line:
                continue

            # 👉 寫檔
            f.write(line)
            f.flush()

            # 👉 runtime 計算
            elapsed = time.time() - start_time

            # 👉 檔案大小（bytes）
            size_bytes = f.tell()

            # 👉 轉成 MB
            size_mb = size_bytes / (1024 * 1024)

            try:
                msg = pynmea2.parse(line.decode('ascii', errors='ignore'))

                if isinstance(msg, pynmea2.types.talker.GGA):
                    utc_time = datetime.combine(datetime.today(), msg.timestamp)
                    local_time = utc_time + timedelta(hours=8)

                    print(f"""
Uptime: {elapsed:.1f} sec
File size: {size_mb:.2f} MB

Time (UTC+8): {local_time.time()}
Fix: {msg.gps_qual}
Satellites: {msg.num_sats}
HDOP: {msg.horizontal_dil}
Altitude: {msg.altitude} m
""")

            except pynmea2.ParseError:
                pass

        except Exception as e:
            print("Error:", e)

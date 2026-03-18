import serial
import pynmea2
from datetime import datetime

# 👉 產生初始化時間檔名
start_time = datetime.now().strftime("%y%m%d%H%M%S")
filename = f"gnss_log_{start_time}.bin"

print(f"Logging to: {filename}")

ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)

with open(filename, 'ab') as f:
    while True:
        try:
            line = ser.readline()

            if not line:
                continue

            # 👉 存原始資料
            f.write(line)
            f.flush()

            # 👉 解析 NMEA
            try:
                msg = pynmea2.parse(line.decode('ascii', errors='ignore'))

                if isinstance(msg, pynmea2.types.talker.GGA):
                    print(f"""
Time: {msg.timestamp}
Fix: {msg.gps_qual}
Satellites: {msg.num_sats}
HDOP: {msg.horizontal_dil}
Altitude: {msg.altitude} m
""")

            except pynmea2.ParseError:
                pass

        except Exception as e:
            print("Error:", e)
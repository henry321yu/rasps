import serial
from pyubx2 import UBXReader
import time
from datetime import datetime, timedelta

ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)

ubr = UBXReader(ser)

start_time = time.time()

with open('gnss_log.bin', 'ab') as f:
    while True:
        try:
            raw, parsed = ubr.read()

            if raw:
                f.write(raw)
                f.flush()

            if parsed and parsed.identity == "NAV-PVT":

                elapsed = time.time() - start_time
                size_mb = f.tell() / (1024 * 1024)

                # 👉 GNSS UTC
                dt = datetime(
                    parsed.year, parsed.month, parsed.day,
                    parsed.hour, parsed.min, parsed.second
                )

                # 👉 轉 UTC+8
                local_time = dt + timedelta(hours=8)

                # 👉 精度（mm → m）
                hAcc = parsed.hAcc / 1000
                vAcc = parsed.vAcc / 1000

                print(f"""
Uptime: {elapsed:.1f} sec
File size: {size_mb:.2f} MB

Time (UTC+8): {local_time}
FixType: {parsed.fixType}
Satellites: {parsed.numSV}

Horizontal Accuracy: {hAcc:.3f} m
Vertical Accuracy: {vAcc:.3f} m
""")

        except Exception as e:
            print("Error:", e)
import serial
import time

ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)

with open('gnss_log.txt', 'ab') as f:
    while True:
        data = ser.read(1024)
        if data:
            print(f"Read {len(data)} bytes")
            print(f"{data}")
            f.write(data)
            f.flush()
        else:
            print("No data")

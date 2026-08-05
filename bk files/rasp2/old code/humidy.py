import serial
import time

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
time.sleep(2)

while True:
    line = ser.readline().decode('utf-8').strip()
    
    if line:
        try:
            humidity = float(line)
            print(f"{humidity:.2f} %")
        except:
            pass

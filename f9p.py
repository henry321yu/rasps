import serial
import time

while True:
    try:
        print("Connecting...")
        ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)

        with open('gnss_log.bin', 'ab') as f:
            while True:
                data = ser.read(1024)
                if data:
                    print(f"{len(data)} bytes")
                    f.write(data)
                    f.flush()

    except serial.SerialException as e:
        print(f"Serial error: {e}")
        time.sleep(2)
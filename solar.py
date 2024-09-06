import serial
import time
import RPi.GPIO as GPIO

uart = serial.Serial('/dev/serial0', 9600, timeout=1)

def set_HC12():
    uart = serial.Serial('/dev/serial0', 9600, timeout=1)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(18,GPIO.OUT)
    GPIO.output(18,0)
    time.sleep(0.1)
    uart.write(b'AT+B115200\r\n')
    time.sleep(0.1)
    uart = serial.Serial('/dev/serial0', 115200, timeout=1)
    time.sleep(0.1)
    uart.write(b'AT+B115200\r\n')
    time.sleep(0.1)
    uart.write(b'AT+C087\r\n')
    time.sleep(0.1)
    uart.write(b'AT+P8\r\n')
    time.sleep(0.1) 
    GPIO.output(18,1)

set_HC12()

while True:
    try:
        data = uart.readline().decode('utf-8').rstrip()
        if data:
            print(data)
        else:
            time.sleep(0.01)
    except serial.SerialException as e:
        print(f"SerialException: {e}")
        uart.close()
        uart = serial.Serial('/dev/serial0', 115200, timeout=1)
        time.sleep(0.01)

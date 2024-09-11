import time
import serial
import math
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

def read_HC12():
    global volt,current,batt
    volt=current=batt=0
    try:
        uart = serial.Serial('/dev/serial0', 115200, timeout=1)
        data = uart.readline().decode('utf-8', errors='ignore').rstrip()
        if data:        
#             print(data)
            parts = data.split(",")
            if len(parts) == 3:
                try:
                    volt=float(parts[0])
                    current=float(parts[1])
                    batt=float(parts[2])
                except:
                    time.sleep(0.001)
        else:
            time.sleep(0.001)
    except serial.SerialException as e:
#         print(f"SerialException: {e}")
#         uart.close()
#         uart = serial.Serial('/dev/serial0', 115200, timeout=1)
        time.sleep(0.001)
        
set_HC12()

t0 = time.time()
i = 0

while True:
    t = time.time() - t0
    read_HC12()
    if True:

        msg = ''
        msg += str(round(t, 3))
        msg += '\t'    
        msg += str(round(volt, 2))
        msg += '\t'
        msg += str(round(current, 2))
        msg += '\t'
        msg += str(round(batt, 2))
        msg += '\n'
        
        print(msg,end='')
        time.sleep(1)




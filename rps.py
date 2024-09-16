import time
import serial
import math
import RPi.GPIO as GPIO
from datetime import datetime
import os

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
            parts = data.split(",")
            if len(parts) == 3:
                try:
                    volt=float(parts[0])
                    current=float(parts[1])
#                     batt=float(parts[2])
                    batt=v2p(volt)
                except:
                    time.sleep(0.001)
        else:
            time.sleep(0.001)
    except serial.SerialException as e:
        time.sleep(0.001)
        
def v2p(voltage):
    maxv = 12.7
    minv = 11.3
    if voltage >= maxv:
        return 100.0
    elif voltage <= minv:
        return 0.0
    else:
        percentage = (voltage - minv) / (maxv - minv) * 100
        return percentage


uart = serial.Serial('/dev/serial0', 9600, timeout=1)

current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
print("current time :", current_datetime)
# log_folder = r'C:\Users\sgrc-325\Desktop\py\log'
# log_folder = r'C:\Users\弘銘\Desktop\WFH\git\log'
log_folder = r'/home/rasp3/Desktop/log'
log_filename = f'logger_P_{current_datetime}.csv'
log_filepath = os.path.join(log_folder, log_filename)

if not os.path.exists(log_folder):
    os.makedirs(log_folder)
    
log = open(log_filepath, 'w+', encoding="utf8")
        
set_HC12()

t0 = time.time()
i = 0
t1 = 0

while True:
    t = time.time() - t0
    read_HC12()
    if True:
        current_datetime = datetime.now().strftime("%H:%M:%S")
        if (t-t1>=10)&(volt>0):
            t1 = t

            msg = ''
            msg += str(round(t, 3))
            msg += '\t'    
            msg += str(current_datetime)
            msg += '\t'
            msg += str(round(volt, 2))
            msg += '\t'
            msg += str(round(current, 2))
            msg += '\t'
            msg += str(round(batt, 2))
            msg += '\n'
            
            print(msg,end='')
            log.write(msg)
            log.flush()
import time
import smbus2
import socket
import os
from datetime import datetime

DEVID_AD = 0x00 #ADXL355BZ
DEVID_MST = 0x01
PARTID = 0x02
REVID = 0x03
STATUS = 0x04
FIFO_ENTRIES = 0x05
TEMP2 = 0x06
TEMP1 = 0x07
XDATA3 = 0x08
XDATA2 = 0x09
XDATA1 = 0x0A
YDATA3 = 0x0B
YDATA2 = 0x0C
YDATA1 = 0x0D
ZDATA3 = 0x0E
ZDATA2 = 0x0F
ZDATA1 = 0x10
FIFO_DATA = 0x11
OFFSET_X_H = 0x1E
OFFSET_X_L = 0x1F
OFFSET_Y_H = 0x20
OFFSET_Y_L = 0x21
OFFSET_Z_H = 0x22
OFFSET_Z_L = 0x23
ACT_EN = 0x24
ACT_THRESH_H = 0x25
ACT_THRESH_L = 0x26
ACT_COUNT = 0x27
FILTER = 0x28
FIFO_SAMPLES = 0x29
INT_MAP = 0x2A
SYNC = 0x2B
RANGE = 0x2C
POWER_CTL = 0x2D
SELF_TEST = 0x2E
RESET = 0x2F

HOST = "140.116.45.98"  # office pc
# HOST = "140.116.45.14"  # fly pc
PORT = 5566
    
def write_355(addr,value):
        bus.write_byte_data(Device_Address, addr, value)
        
def read_355_m():
    global var,ax,ay,az,temp
    var=bus.read_i2c_block_data(0x1D,TEMP2,11)
    
    ax=(var[2]<<12|var[3]<<4|var[4]>>4)
    ay=(var[5]<<12|var[6]<<4|var[7]>>4)
    az=(var[8]<<12|var[9]<<4|var[10]>>4)
    
    rangee=0x3E800 # 2g
#     rangee=0x1F400 # 4g
#     rangee=0xFA00 # 8g
    
    if(ax > 0x80000):
        ax = ax - 0x100000
    ax=ax/rangee
    if(ay > 0x80000):
        ay = ay - 0x100000
    ay=ay/rangee
    if(az > 0x80000):
        az = az - 0x100000
    az=az/rangee      
    
    temp=(var[0]<<8|var[1])
    temp=((1852-temp)/9.05)+27.2  #need calibrate
    
    
bus = smbus2.SMBus(1) # or bus = smbus.SMBus(0) for older version boards

# set ADXL355 device address
Device_Address = 0x1D #ADXL355 device address
write_355(RESET, 0x52);  # reset sensor
time.sleep(0.1)
write_355(POWER_CTL, 0x00);  # writing 0 to to enable sensor
time.sleep(0.03)
write_355(RANGE, 0x01);
time.sleep(0.03)
write_355(SELF_TEST, 0x00);  # writing 3 to to enable self test,0 for disble
time.sleep(0.1)

current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
print("current time :",current_datetime)
log_folder = r'/home/rasp1/Desktop/log'
log_filename = f'logger_RP_{current_datetime}.csv'
log_filepath = os.path.join(log_folder, log_filename)

if not os.path.exists(log_folder):
    os.makedirs(log_folder)

log = open(log_filepath, 'w+', encoding="utf8")

print('Connecting..',HOST)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))


t0=time.time()

while True:
    t=time.time()-t0
    read_355_m()   
    
    num=6
    
    msg=''    
    msg += str(round(t, 3))
    msg += '\t'
    msg += str(round(ax, num))
    msg += '\t'
    msg += str(round(ay, num))
    msg += '\t'
    msg += str(round(az, num))
    msg += '\t'
    msg += str(round(temp, num))
    msg += '\n'
    
    s.send(bytes(msg,"utf-8"))
    log.write(msg)
    print(msg)
#     time.sleep(0.05)




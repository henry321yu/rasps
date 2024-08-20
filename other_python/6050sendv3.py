import socket
import time
# import smbus
from smbus2 import SMBus
# from .smbus2 import SMBus
# import spidev

PWR_MGMT_1   = 0x6B
SMPLRT_DIV   = 0x19
MPU_CONFIG   = 0x1A
GYRO_CONFIG  = 0x1B
ACCEL_CONFIG = 0x1C
INT_ENABLE   = 0x38
ACCEL_XOUT_H = 0x3B
ACCEL_YOUT_H = 0x3D
ACCEL_ZOUT_H = 0x3F
GYRO_XOUT_H  = 0x43
GYRO_YOUT_H  = 0x45
GYRO_ZOUT_H  = 0x47


HEADERSIZE = 10

HOST = "140.116.45.98"  # office pc
PORT = 5566

def read_raw_data(addr):
        high = bus.read_byte_data(Device_Address, addr)
        low = bus.read_byte_data(Device_Address, addr+1)
        value = ((high << 8) | low)
        if(value > 32768):
            value = value - 65536
        return value
    
def write_data(addr,value):
        # First change it to 0x00 to make sure we write the correct value later
        bus.write_byte_data(Device_Address, addr, 0x00)
        bus.write_byte_data(Device_Address, addr, value)

    
bus = smbus.SMBus(1) # or bus = smbus.SMBus(0) for older version boards
Device_Address = 0x68   # MPU6050 device address

# set MPU6050 device address
Device_Address = 0x68   # MPU6050 device address
write_data(ACCEL_CONFIG,0x00)
write_data(GYRO_CONFIG,0x00)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))

while True:
    acc_x = read_raw_data(ACCEL_XOUT_H)
    acc_y = read_raw_data(ACCEL_YOUT_H)
    acc_z = read_raw_data(ACCEL_ZOUT_H)
    gyro_x = read_raw_data(GYRO_XOUT_H)
    gyro_y = read_raw_data(GYRO_YOUT_H)
    gyro_z = read_raw_data(GYRO_ZOUT_H)

    ax = acc_x/16384.0
    ay = acc_y/16384.0
    az = acc_z/16384.0
    gx = gyro_x/131.0
    gy = gyro_y/131.0
    gz = gyro_z/131.0    
    raw_temp=read_raw_data(0x41)
    temp=(raw_temp / 340.0) + 36.53

    time.sleep(0.05)
    num=3
    
    msg=''    
    msg += str(round(ax, num))
    msg += '\t'
    msg += str(round(ay, num))
    msg += '\t'
    msg += str(round(az, num))
    msg += '\t'
    msg += str(round(gx, num))
    msg += '\t'
    msg += str(round(gy, num))
    msg += '\t'
    msg += str(round(gz, num))
    msg += '\t'
    msg += str(round(temp, num))
    
    s.send(bytes(msg,"utf-8"))
    print(msg)



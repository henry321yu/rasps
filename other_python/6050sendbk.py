6050sendv1.py
import socket
import time
import mpu6050

HEADERSIZE = 10

HOST = "140.116.45.98"  # office pc
PORT = 5566

mpu6050 = mpu6050.mpu6050(0x68)

# mpu6050.set_accel_range(ACCEL_RANGE_2G)
# mpu6050.set_gyro_range(GYRO_RANGE_250DEG)
# mpu6050.set_filter_range(FILTER_BW_256)

def read_sensor_data():
    # Read sensor
    acc = mpu6050.get_accel_data()
    gyr = mpu6050.get_gyro_data()
    temp = mpu6050.get_temp()
    return acc, gyr, temp

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))

while True:
    acc,gyr,temp=read_sensor_data()
#     print("Accelerometer data:", acc)
#     print("Gyroscope data:", gyr)
#     print("Temp:", temp)

    # Wait for 0.1 second
    time.sleep(1)
        
#     msg = "Welcome"
#     msg = f"{len(msg):<{HEADERSIZE}}"+msg

    temp=round(temp, 2)
    temp2="wtf"
    msg = str(temp)
    s.send(bytes(msg,"utf-8"))
#     s.send(bytes("WTF",'utf-8'))
    print(msg)


    
#     while True:
#         time.sleep(1)
#         print(msg)
#         s.send(bytes(msg,"utf-8"))
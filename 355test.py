import time
import smbus2

# ADXL355 註冊位址
TEMP2 = 0x06
XDATA3 = 0x08
YDATA3 = 0x0B
ZDATA3 = 0x0E
POWER_CTL = 0x2D
RANGE = 0x2C
SELF_TEST = 0x2E
RESET = 0x2F

# I2C 位址
Device_Address = 0x1D  # ADXL355 device address
bus = smbus2.SMBus(1)

def write_355(addr, value):
    bus.write_byte_data(Device_Address, addr, value)

def read_355_accel():
    data = bus.read_i2c_block_data(Device_Address, TEMP2, 11)
    
    ax = (data[2] << 12) | (data[3] << 4) | (data[4] >> 4)
    ay = (data[5] << 12) | (data[6] << 4) | (data[7] >> 4)
    az = (data[8] << 12) | (data[9] << 4) | (data[10] >> 4)
    
    range_scale = 0x3E800  # ±2g

    # 補正兩補數格式
    if ax > 0x80000:
        ax -= 0x100000
    if ay > 0x80000:
        ay -= 0x100000
    if az > 0x80000:
        az -= 0x100000

    ax = ax / range_scale
    ay = ay / range_scale
    az = az / range_scale

    return ax, ay, az

# 初始化 ADXL355
write_355(RESET, 0x52)
time.sleep(0.1)
write_355(POWER_CTL, 0x00)
time.sleep(0.03)
write_355(RANGE, 0x01)  # ±2g
time.sleep(0.03)
write_355(SELF_TEST, 0x00)
time.sleep(0.1)

print("Start reading ADXL355...")

while True:
    ax, ay, az = read_355_accel()
    print(f"X: {ax:.6f} g\tY: {ay:.6f} g\tZ: {az:.6f} g")
    time.sleep(0.05)

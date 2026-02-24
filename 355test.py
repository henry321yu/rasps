import time
import smbus2

# ADXL355 Register Map
TEMP2 = 0x06
XDATA3 = 0x08
YDATA3 = 0x0B
ZDATA3 = 0x0E
RESET = 0x2F
POWER_CTL = 0x2D
RANGE = 0x2C
SELF_TEST = 0x2E

# 初始化
bus = smbus2.SMBus(1)
Device_Address = 0x1D
start_time = time.perf_counter()
count = 0
freq = 0.0
azt = 0

def setup_355_m():
    write_355(RESET, 0x52)
    time.sleep(0.1)
    write_355(POWER_CTL, 0x00)
    time.sleep(0.03)
    write_355(RANGE, 0x01)
    time.sleep(0.03)
    write_355(SELF_TEST, 0x00)
    time.sleep(0.1)

def write_355(addr, value):
    bus.write_byte_data(Device_Address, addr, value)

def read_355_m():
    global ax, ay, az, temp
    var = bus.read_i2c_block_data(Device_Address, TEMP2, 11)

    ax = (var[2] << 12 | var[3] << 4 | var[4] >> 4)
    ay = (var[5] << 12 | var[6] << 4 | var[7] >> 4)
    az = (var[8] << 12 | var[9] << 4 | var[10] >> 4)

    rangee = 0x3E800

    if ax > 0x80000:
        ax -= 0x100000
    ax /= rangee

    if ay > 0x80000:
        ay -= 0x100000
    ay /= rangee

    if az > 0x80000:
        az -= 0x100000
    az /= rangee

    temp_raw = (var[0] << 8 | var[1])
    temp = ((1852 - temp_raw) / 9.05) + 27.2  # 溫度校正

setup_355_m() # 設定 ADXL355

# 讀取與印出
while True:
    read_355_m()
    while azt == az:
        read_355_m()

    azt = az
    count += 1
    now = time.perf_counter()
    elapsed = now - start_time

    # 每2秒更新一次頻率
    if elapsed >= 2.0:
        freq = count / elapsed
        count = 0
        start_time = now
        print(f"{ax:.6f},{ay:.6f},{az:.6f},{temp:.2f},{freq:.2f}")

    # print(f"{ax:.6f},{ay:.6f},{az:.6f},{temp:.2f},{freq:.2f}")

    time.sleep(0.0005)
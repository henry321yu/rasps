import time
import smbus2
import RPi.GPIO as GPIO

# ===============================
# ADXL355 Register Map
# ===============================
TEMP2 = 0x06
RESET = 0x2F
POWER_CTL = 0x2D
RANGE = 0x2C
SELF_TEST = 0x2E

# ===============================
# I2C 初始化
# ===============================
bus = smbus2.SMBus(1)
Device_Address = 0x1D

# ===============================
# DRDY GPIO 設定
# ===============================
DRDY_PIN = 17   # BCM numbering

GPIO.setmode(GPIO.BCM)
GPIO.setup(DRDY_PIN, GPIO.IN)

# ===============================
# 頻率統計
# ===============================
start_time = time.perf_counter()
count = 0
freq = 0.0

ax = ay = az = temp = 0.0


# ===============================
# ADXL355 setup
# ===============================
def write_355(addr, value):
    bus.write_byte_data(Device_Address, addr, value)


def setup_355_m():
    write_355(RESET, 0x52)
    time.sleep(0.1)

    write_355(POWER_CTL, 0x00)  # measurement mode
    time.sleep(0.03)

    write_355(RANGE, 0x01)      # ±2g
    time.sleep(0.03)

    write_355(SELF_TEST, 0x00)
    time.sleep(0.1)


# ===============================
# 讀取資料
# ===============================
def read_355_m():
    global ax, ay, az, temp

    var = bus.read_i2c_block_data(Device_Address, TEMP2, 11)

    ax_raw = (var[2] << 12 | var[3] << 4 | var[4] >> 4)
    ay_raw = (var[5] << 12 | var[6] << 4 | var[7] >> 4)
    az_raw = (var[8] << 12 | var[9] << 4 | var[10] >> 4)

    rangee = 0x3E800

    if ax_raw > 0x80000:
        ax_raw -= 0x100000
    if ay_raw > 0x80000:
        ay_raw -= 0x100000
    if az_raw > 0x80000:
        az_raw -= 0x100000

    ax = ax_raw / rangee
    ay = ay_raw / rangee
    az = az_raw / rangee

    temp_raw = (var[0] << 8 | var[1])
    temp = ((1852 - temp_raw) / 9.05) + 27.2


# ===============================
# DRDY Interrupt Callback
# ===============================
def drdy_callback(channel):
    global count, start_time, freq

    read_355_m()
    count += 1

    now = time.perf_counter()
    elapsed = now - start_time

    # 每2秒更新頻率
    if elapsed >= 2.0:
        freq = count / elapsed
        count = 0
        start_time = now

        print(f"{ax:.6f},{ay:.6f},{az:.6f},{temp:.2f},{freq:.2f}")


# ===============================
# 主程式
# ===============================
setup_355_m()

# 丟掉初始化後幾筆不穩定資料（datasheet 建議）
time.sleep(0.5)

# 設定 rising edge interrupt
GPIO.add_event_detect(
    DRDY_PIN,
    GPIO.RISING,
    callback=drdy_callback
)

print("DRDY interrupt started...")

try:
    while True:
        time.sleep(1)   # 主執行緒閒置即可

except KeyboardInterrupt:
    GPIO.cleanup()
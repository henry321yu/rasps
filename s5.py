import time    #發射端
import smbus2
import socket
import os
from datetime import datetime
import serial
import math

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
# HOST = "192.168.105.143"  # my pc
PORT = 5566

i = 0

def write_355(addr, value):
    bus.write_byte_data(Device_Address, addr, value)

def read_355_m():
    global var, ax, ay, az, temp
    var = bus.read_i2c_block_data(0x1D, TEMP2, 11)
    
    ax = (var[2] << 12 | var[3] << 4 | var[4] >> 4)
    ay = (var[5] << 12 | var[6] << 4 | var[7] >> 4)
    az = (var[8] << 12 | var[9] << 4 | var[10] >> 4)
    
    rangee = 0x3E800  # 2g
    if ax > 0x80000:
        ax -= 0x100000
    ax = ax / rangee
    if ay > 0x80000:
        ay -= 0x100000
    ay = ay / rangee
    if az > 0x80000:
        az -= 0x100000
    az = az / rangee
    
    temp = (var[0] << 8 | var[1])
    temp = ((1852 - temp) / 9.05) + 27.2  # 需要校準

# 計算兩組經緯度間的距離（單位：米），使用Haversine公式
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # 地球半徑（米）
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance

def parse_nmea_sentence(nmea_sentence):
    parts = nmea_sentence.split(',')
    
    if parts[0] == '$GNGGA':  # GGA 句子包含時間、位置和質量指標數據
        try:
            # 解析時間（UTC時間）
            time_utc = parts[1]
            hours = int(time_utc[0:2]) + 8  # +8 為台灣時間
            minutes = int(time_utc[2:4])
            seconds = float(time_utc[4:])

            # 解析經度與緯度
            lat = float(parts[2])
            lat_dir = parts[3]
            lon = float(parts[4])
            lon_dir = parts[5]
            altitude = float(parts[9])  # 高程（海拔）

            # 解析GPS模式
            gps_quality = int(parts[6])  # GPS模式質量指標
            gps_mode = interpret_gps_mode(gps_quality)

            # 轉換經緯度到十進位格式
            lat = convert_to_decimal_degrees(lat, lat_dir)
            lon = convert_to_decimal_degrees(lon, lon_dir)

            # 格式化時間
            formatted_time = f"{hours:02}:{minutes:02}:{seconds:05.2f}"

            return formatted_time, lat, lon, altitude, gps_mode
        except (ValueError, IndexError):
            # 無效的數據格式或數據不完整
            return None
    return None

def interpret_gps_mode(gps_quality):
    # 解析GPS模式
    modes = {
        0: 0,  # 無效
        1: 1,  # GPS Fix
        2: 2,  # DGPS Fix
        4: 4,  # RTK Fixed
        5: 5   # RTK Float
    }
    return modes.get(gps_quality, -1)  # -1 代表未知的模式

def convert_to_decimal_degrees(value, direction):
    # 轉換NMEA格式的度分（ddmm.mmmm）到十進位格式
    degrees = int(value // 100)
    minutes = value % 100
    decimal_degrees = degrees + minutes / 60

    if direction in ['S', 'W']:
        decimal_degrees = -decimal_degrees

    return decimal_degrees

# 設定串口參數
port = '/dev/ttyACM0'  # 替換為實際的串口號，例如'/dev/ttyACM0'
baud_rate = 9600  # 默認的通訊速率為9600
timeout = 1  # 設定超時為1秒

# 設定目標座標
target_lat = 23.021753398  # 目標緯度
target_lon = 120.196166998  # 目標經度

bus = smbus2.SMBus(1)  # 或使用 bus = smbus.SMBus(0) 來支持舊版板子

# 設定 ADXL355 設備地址
Device_Address = 0x1D  # ADXL355 設備地址
write_355(RESET, 0x52)  # 重置傳感器
time.sleep(0.1)
write_355(POWER_CTL, 0x00)  # 寫入 0 以啟用傳感器
time.sleep(0.03)
write_355(RANGE, 0x01)
time.sleep(0.03)
write_355(SELF_TEST, 0x00)  # 寫入 0 以禁用自檢
time.sleep(0.1)

current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
print("current time :", current_datetime)
log_folder = r'/home/rasp1/Desktop/log'
log_filename = f'logger_RP_{current_datetime}.csv'
log_filepath = os.path.join(log_folder, log_filename)

if not os.path.exists(log_folder):
    os.makedirs(log_folder)

log = open(log_filepath, 'w+', encoding="utf8")

# 嘗試建立網路連接
def connect_to_server():
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORT))
            print('Connected to server.')
            return s
        except (socket.error, ConnectionRefusedError) as e:
            print(f"Network error: {e}. Retrying in 5 seconds...")
            time.sleep(5)

s = connect_to_server()
network = "connected"

ser = serial.Serial(port, baud_rate, timeout=timeout)

t0 = time.time()

while True:
    t = time.time() - t0
    
    # 讀取並解碼NMEA句子
    nmea_sentence = ser.readline().decode('ascii', errors='replace')
    
    # 解析時間、經緯度、高程、GPS模式
    result = parse_nmea_sentence(nmea_sentence)
    
    if result:
        time_utc, lat, lon, altitude, gps_mode = result
        # 計算與目標座標的距離誤差
        distance_error = calculate_distance(lat, lon, target_lat, target_lon)
        
        read_355_m()
        
        i += 1
        f = i / t
        delay = 0.005
        
        num = 6
        
        msg = ''
        msg += str(round(t, 3))
        msg += '\t'
        msg += str(time_utc)
        msg += '\t'
        msg += str(round(ax, num))
        msg += '\t'
        msg += str(round(ay, num))
        msg += '\t'
        msg += str(round(az, num))
        msg += '\t'
        
        msg += str(round(lat, 10))
        msg += '\t'
        msg += str(round(lon, 10))
        msg += '\t'
        msg += str(round(altitude, 5))
        msg += '\t'
        msg += str(gps_mode)
        msg += '\t'
        msg += str(round(distance_error, 4))
        msg += '\t'    
        msg += str(round(temp, 2))
        
        print(msg)
        log.write(msg + '\n')
        log.flush()
        
        # 嘗試發送數據到伺服器
        try:
            s.sendall(msg.encode('utf-8'))
        except (socket.error, BrokenPipeError) as e:
            print(f"Network error while sending data: {e}. Reconnecting...")
            s.close()
            s = connect_to_server()

    else:
        print("No valid NMEA sentence received.")
        # 如果在一定時間內沒有接收到數據，可以考慮重新連接串口或網路

    time.sleep(delay)

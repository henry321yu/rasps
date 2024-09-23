import time    #發射端   # s5.py
import smbus2
import socket
import os
from datetime import datetime
import serial
import math
import shutil
import serial # 電
import RPi.GPIO as GPIO # 電

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

SERVERS = [
    {"HOST": "140.116.45.98", "PORT": 5566},  # server 1
    {"HOST": "140.116.45.14", "PORT": 5566},  # server 2
]

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

recording_duration = 2
# Function to get the current log file name based on the current time
def get_log_file_name():
    current_time = datetime.now()
    minute = (current_time.minute // recording_duration) * recording_duration  # Round down to the nearest 10 minutes
    time_str = current_time.strftime(f"%Y%m%d_%H{minute:02d}")
    log_filename = f'logger_PC_{time_str}.txt'    
    return os.path.join(log_folder, log_filename)




uart = serial.Serial('/dev/serial0', 9600, timeout=1) # 電

def set_HC12():      # 電
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

def read_HC12():      # 電
    global volt,current,batt
    volt=current=batt=0
    try:
        uart = serial.Serial('/dev/serial0', 115200, timeout=1)
        data = uart.readline().decode('utf-8', errors='ignore').rstrip()
        if data:        
            parts = data.split(",")
            if len(parts) == 3 :                
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
        
def v2p(voltage):       # 電
    maxv = 12.7
    minv = 11.3
    if voltage >= maxv:
        return 100.0
    elif voltage <= minv:
        return 0.0
    else:
        percentage = (voltage - minv) / (maxv - minv) * 100
        return percentage


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
# log_folder = r'/home/rasp3/Desktop/log'
log_folder = r'/home/rasp3/Desktop/log_test_by_fly'
# log_folder = r'C:\Users\fly\GB_Sar_and_GPS\log'
# log_filename = f'logger_RP_{current_datetime}.csv'
# log_filepath = os.path.join(log_folder, log_filename)

if not os.path.exists(log_folder):
    os.makedirs(log_folder)


# 設定資料夾路徑
# folder_path = "your_folder_path_here"  # 替換為你的資料夾路徑

# # 設定伺服器的 HOST 和 PORT
# HOST = 'your_server_host'  # 替換為伺服器的IP
# PORT = your_server_port  # 替換為伺服器的Port

# 建立 socket 連線
def send_file_over_network():
    for server in SERVERS:
        HOST = server["HOST"]
        PORT = server["PORT"]
        
        try:
            # 建立與伺服器的連線
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)  # 設定超時時間為 5 秒
            s.connect((HOST, PORT))
            print(f'Connected to {HOST}:{PORT}')

            # 獲取資料夾中所有 .txt 檔案
            txt_files = [f for f in os.listdir(log_folder) if f.endswith('.txt')]

            # 傳送檔案名稱
            current_time = datetime.now()
            # 格式化日期和時間
            FN = "logger_" + current_time.strftime("%Y%m%d_%H%M%S") + ".txt"
            s.sendall(f"FILENAME:{FN}".encode('utf-8'))
            
            for file_name in txt_files:
                file_path = os.path.join(log_folder, file_name)
                
                # 傳送檔案內容
                with open(file_path, 'r', encoding='utf-8') as file:
                    for line in file:
                        s.sendall(line.encode('utf-8'))  # 傳送每行的內容
                        print(f'Sent line to {HOST}:{PORT}: {line.strip()}')

                ######### 移動並刪除檔案
                folder_C = r'/home/rasp3/Desktop/log_backup_by_fly'  # 替換成資料夾 C 的路徑
                file_B_path_A = file_path
                file_path_backup = os.path.join(folder_C, file_name)

                try:
                    shutil.move(file_path, file_path_backup)
                    if os.path.exists(file_path_backup) and os.path.exists(file_path):
                        os.remove(file_path)
                        print(f'Moved and removed file {file_name} for {HOST}:{PORT}')
                    else:
                        print(f'Failed to remove file {file_name}')
                except FileNotFoundError as e:
                    print(f"Error: {e}")

            # 加入檔案結束標記，以便伺服器識別
            s.sendall(b'END_OF_FILE')

            print(f"All files have been sent to {HOST}:{PORT}.")
            s.close()  # 傳送完畢後關閉 socket 連線

        except Exception as e:
            print(f"Failed to connect to {HOST}:{PORT} within 5 seconds. Error: {e}")

# # 呼叫函數來進行檔案傳輸
# send_file_over_network()


# 嘗試建立網路連接
def connect_to_server():
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORT))
            print('Connected to server.')
            return s
        except (socket.error, ConnectionRefusedError) as e:
            print(f"Network error: {e}. Retrying in 1 seconds...")
            time.sleep(1)

# s = connect_to_server()
# print('Connected !')

ser = serial.Serial(port, baud_rate, timeout=timeout)

set_HC12()    # 電

t0 = time.time()
i = 0

# Initialize the log file
# log_filepath = get_log_file_name()
log_data = []

# 開啟初始檔案
current_log_filepath = get_log_file_name()
file = open(current_log_filepath, 'a')

log_filepath = current_log_filepath

log = open(current_log_filepath, 'w+', encoding="utf8")

start_time_KK = datetime.now()

delay = 0.005

while True:
    t = time.time() - t0
    
    # 讀取並解碼NMEA句子
    nmea_sentence = ser.readline().decode('ascii', errors='replace')
    
    # 解析時間、經緯度、高程、GPS模式
    result = parse_nmea_sentence(nmea_sentence)
    
    if result:
        time_utc, lat, lon, altitude, gps_mode = result        
        read_355_m()
        read_HC12() # 電
        
        i += 1
        f = i / t
        num = 6
        
        msg = ''
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
        msg += str(round(temp, 2))
        
        msg += '\t'
        msg += str(round(volt, 2)) # 電
        msg += '\t'
        msg += str(round(current, 2))   # 電
        
        msg += '\n'
        
        recording_Hz = 0.1 #0.2
        if (datetime.now() - start_time_KK ).seconds > 1/recording_Hz :

            print(msg,end='')

            start_time_KK = datetime.now()

            
            
            # world_time = str(time_utc)  # 世界時間
            # acc_x = str(round(ax, num))
            # acc_y = str(round(ay, num))
            # acc_z = str(round(az, num))
            # lat = str(round(lat, 10))  # 緯度
            # lon = str(round(lon, 10))  # 經度
            # alt = str(round(altitude, 5))  # 高程
            # gps_mode = str(gps_mode)  # GPS模式
            # temperature = str(round(temp, 2))  # 溫度

            # # Log the message
            # log_data.append([world_time, acc_x, acc_y, acc_z, lat, lon, alt, gps_mode, temperature])

            # 寫入檔案
            file.write(msg)
            file.flush()  # 確保立即寫入磁碟

            current_log_filepath = get_log_file_name()
            
            if current_log_filepath != log_filepath:
                # Save log data to a CSV file
                file.close()  # 關閉目前的檔案

                # 呼叫函數來進行檔案傳輸
                send_file_over_network()
                
                filename = current_log_filepath  # 產生新的檔名
                file = open(filename, 'a')  # 開啟新檔案
            
                log_filepath = current_log_filepath
                log_data = []







    # 這裡可以加入適當的休息時間
    # time.sleep(1)

        
        # log.write(msg)
        # log.flush()
        
        # # 嘗試發送數據到伺服器
        # try:
        #     s.sendall(msg.encode('utf-8'))
        # except (socket.error, BrokenPipeError) as e:
        #     print(f"Network error while sending data: {e}. Reconnecting...")
        #     s.close()
        #     s = connect_to_server()

#     else:
#         print("No valid NMEA sentence received.")
        # 如果在一定時間內沒有接收到數據，可以考慮重新連接串口或網路

    time.sleep(delay)




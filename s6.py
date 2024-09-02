import time
import smbus2
import socket
import os
from datetime import datetime
import serial
import math

# ADXL355 寄存器地址
DEVID_AD = 0x00
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

# 设置主机和端口
HOST = "0.0.0.0"  # 服务器监听所有可用的IP地址
PORT = 5566

# I2C setup
bus = smbus2.SMBus(1)
Device_Address = 0x1D  # ADXL355 Device Address

def write_355(addr, value):
    bus.write_byte_data(Device_Address, addr, value)

def read_355_m():
    global ax, ay, az, temp
    var = bus.read_i2c_block_data(Device_Address, TEMP2, 11)
    ax = (var[2] << 12 | var[3] << 4 | var[4] >> 4)
    ay = (var[5] << 12 | var[6] << 4 | var[7] >> 4)
    az = (var[8] << 12 | var[9] << 4 | var[10] >> 4)

    rangee = 0x3E800  # 2g
    ax = (ax - 0x100000 if ax > 0x80000 else ax) / rangee
    ay = (ay - 0x100000 if ay > 0x80000 else ay) / rangee
    az = (az - 0x100000 if az > 0x80000 else az) / rangee

    temp = ((1852 - (var[0] << 8 | var[1])) / 9.05) + 27.2

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = map(math.radians, [lat1, lat2])
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (math.sin(delta_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def parse_nmea_sentence(nmea_sentence):
    parts = nmea_sentence.split(',')
    if parts[0] == '$GNGGA':
        try:
            time_utc = parts[1]
            hours, minutes, seconds = int(time_utc[:2]) + 8, int(time_utc[2:4]), float(time_utc[4:])
            lat = float(parts[2])
            lat_dir = parts[3]
            lon = float(parts[4])
            lon_dir = parts[5]
            altitude = float(parts[9])
            gps_quality = int(parts[6])
            gps_mode = interpret_gps_mode(gps_quality)
            lat = convert_to_decimal_degrees(lat, lat_dir)
            lon = convert_to_decimal_degrees(lon, lon_dir)
            formatted_time = f"{hours:02}:{minutes:02}:{seconds:05.2f}"
            return formatted_time, lat, lon, altitude, gps_mode
        except (ValueError, IndexError):
            return None
    return None

def interpret_gps_mode(gps_quality):
    modes = {0: 0, 1: 1, 2: 2, 4: 4, 5: 5}
    return modes.get(gps_quality, -1)

def convert_to_decimal_degrees(value, direction):
    degrees = int(value // 100)
    minutes = value % 100
    decimal_degrees = degrees + minutes / 60
    return -decimal_degrees if direction in ['S', 'W'] else decimal_degrees

port = '/dev/ttyACM0'
baud_rate = 9600
timeout = 1

target_lat = 23.021753398
target_lon = 120.196166998

write_355(RESET, 0x52)
time.sleep(0.1)
write_355(POWER_CTL, 0x00)
time.sleep(0.03)
write_355(RANGE, 0x01)
time.sleep(0.03)
write_355(SELF_TEST, 0x00)
time.sleep(0.1)

current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
print("current time :", current_datetime)
log_folder = r'/home/rasp1/Desktop/log'
log_filename = f'logger_RP_{current_datetime}.csv'
log_filepath = os.path.join(log_folder, log_filename)

if not os.path.exists(log_folder):
    os.makedirs(log_folder)

log = open(log_filepath, 'w+', encoding="utf8")

# 设置Socket服务器
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"Server listening on {HOST}:{PORT}")

    conn, address = server_socket.accept()
    with conn:
        print(f"Connection from {address} established.")
        ser = serial.Serial(port, baud_rate, timeout=timeout)

        t0 = time.time()
        i = 0

        while True:
            t = time.time() - t0
            nmea_sentence = ser.readline().decode('ascii', errors='replace')
            result = parse_nmea_sentence(nmea_sentence)

            if result:
                time_utc, lat, lon, altitude, gps_mode = result
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
                msg += '\n'
                
                print(msg)
                log.write(msg)
                log.flush()

                try:
                    conn.sendall(msg.encode('utf-8'))
                except (socket.error, BrokenPipeError) as e:
                    print(f"Network error while sending data: {e}. Closing connection.")
                    break

            else:
                print("No valid NMEA sentence received.")

            time.sleep(delay)

log.close()

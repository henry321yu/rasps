from smbus2 import SMBus
from pyubx2 import UBXReader, UBXMessage
import math
import time

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

def parse_ubx_message(msg):
    if msg.identity == 'NAV-PVT':  # NAV-PVT 消息包含時間、位置和質量指標數據
        try:
            # 解析時間（UTC時間）
            hours = msg.hour
            minutes = msg.min
            seconds = msg.sec

            # 解析經度與緯度
            lat = msg.lat / 1e7  # 轉換為度
            lon = msg.lon / 1e7  # 轉換為度
            altitude = msg.hMSL / 1e3  # 高程（海拔），轉換為米

            # 解析GPS模式
            fix_type = msg.fixType  # GPS模式質量指標
            gps_mode = interpret_gps_mode(fix_type)

            # 格式化時間
            formatted_time = f"{hours:02}:{minutes:02}:{seconds:02} UTC"

            return formatted_time, lat, lon, altitude, gps_mode
        except (ValueError, AttributeError):
            # 無效的數據格式或數據不完整
            return None
    return None

def interpret_gps_mode(fix_type):
    # 解析GPS模式
    modes = {
        0: "No Fix",
        1: "Dead Reckoning Only",
        2: "2D Fix",
        3: "3D Fix",
        4: "GNSS + Dead Reckoning Combined",
        5: "Time Only Fix"
    }
    return modes.get(fix_type, "Unknown")

# 設定I2C參數
i2c_address = 0x42  # ZED-F9P的I2C地址
bus = SMBus(1)  # 使用I2C總線1

# 設定目標座標
target_lat = 25.0330  # 目標經度，例如台北101
target_lon = 121.5654  # 目標緯度

try:
    while True:
        # 從I2C讀取數據
        data = bus.read_i2c_block_data(i2c_address, 0xFF, 100)  # 讀取最多100字節
        ubr = UBXReader(data)
        
        for msg in ubr:
            result = parse_ubx_message(msg)
            
            if result:
                time_utc, lat, lon, altitude, gps_mode = result
                # 計算與目標座標的距離誤差
                distance_error = calculate_distance(lat, lon, target_lat, target_lon)
                print(f"Time: {time_utc}, Latitude: {lat}, Longitude: {lon}, Altitude: {altitude} m, GPS Mode: {gps_mode}, Distance Error: {distance_error:.2f} m")
        
        time.sleep(1)  # 每秒更新一次
        
except KeyboardInterrupt:
    print("程式終止")
finally:
    bus.close()

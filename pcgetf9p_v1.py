import serial
import math

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
    
    if parts[0] == '$GNGGA':  # GGA句子包含時間、位置和質量指標數據
        try:
            # 解析時間（UTC時間）
            time_utc = parts[1]
            hours = int(time_utc[0:2])+8 # +8 為台灣時間
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
        0: "Invalid",
        1: "GPS Fix",
        2: "DGPS Fix",
        4: "RTK Fixed",
        5: "RTK Float"
    }
    return modes.get(gps_quality, "Unknown")

def convert_to_decimal_degrees(value, direction):
    # 轉換NMEA格式的度分（ddmm.mmmm）到十進位格式
    degrees = int(value // 100)
    minutes = value % 100
    decimal_degrees = degrees + minutes / 60

    if direction in ['S', 'W']:
        decimal_degrees = -decimal_degrees

    return decimal_degrees

# 設定串口參數
port = 'COM18'  # 替換為實際的COM口號，例如'COM3'或'/dev/ttyUSB0'
baud_rate = 9600  # 默認的通訊速率為9600
timeout = 1  # 設定超時為1秒

# 設定目標座標
target_lat = 22.9974118333  # 目標經度，例如台北101
target_lon = 120.2217880000  # 目標緯度

# 開啟串口
ser = serial.Serial(port, baud_rate, timeout=timeout)

try:
    while True:
        # 讀取並解碼NMEA句子
        nmea_sentence = ser.readline().decode('ascii', errors='replace')
        
        # 解析時間、經緯度、高程、GPS模式
        result = parse_nmea_sentence(nmea_sentence)
        
        if result:
            time_utc, lat, lon, altitude, gps_mode = result
            # 計算與目標座標的距離誤差
            distance_error = calculate_distance(lat, lon, target_lat, target_lon)
            print(f"{time_utc}, lat: {lat:.10f}, lon: {lon:.10f}, alt: {altitude:.2f} m, mode: {gps_mode}, bia: {distance_error:.2f} m")
        
except KeyboardInterrupt:
    print("程式終止")
finally:
    ser.close()

import serial

def parse_nmea_sentence(nmea_sentence):
    parts = nmea_sentence.split(',')
    
    if parts[0] == '$GPGGA':  # GGA是全球定位系統修正數據
        try:
            # 解析時間（UTC時間）
            time_utc = parts[1]
            hours = int(time_utc[0:2])
            minutes = int(time_utc[2:4])
            seconds = float(time_utc[4:])

            # 解析經度與緯度
            lat = float(parts[2])
            lat_dir = parts[3]
            lon = float(parts[4])
            lon_dir = parts[5]
            altitude = float(parts[9])  # 高程（海拔）

            # 轉換經緯度到十進位格式
            lat = convert_to_decimal_degrees(lat, lat_dir)
            lon = convert_to_decimal_degrees(lon, lon_dir)

            # 格式化時間
            formatted_time = f"{hours:02}:{minutes:02}:{seconds:05.2f} UTC"

            return formatted_time, lat, lon, altitude
        except (ValueError, IndexError):
            # 無效的數據格式或數據不完整
            return None
    return None

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

# 開啟串口
ser = serial.Serial(port, baud_rate, timeout=timeout)

try:
    while True:
        # 讀取並解碼NMEA句子
        nmea_sentence = ser.readline().decode('ascii', errors='replace')
        
        # 解析時間、經緯度與高程
        result = parse_nmea_sentence(nmea_sentence)
        
        if result:
            time_utc, lat, lon, altitude = result
            print(f"Time: {time_utc}, Latitude: {lat}, Longitude: {lon}, Altitude: {altitude} m")
        
except KeyboardInterrupt:
    print("程式終止")
finally:
    ser.close()

import socket  # 接收端
from time import sleep, strftime, time
import os
from IPython.display import clear_output
from datetime import datetime
import matplotlib.pyplot as plt
import math

HEADERSIZE = 10

# HOST = "104.116.45.14"  # office pc
# HOST = "104.116.45.98"  # fly pc
HOST = "0.0.0.0"  # my pc
# PORT = 5566
PORT = 5567  # my pc

# 指定經緯度的原點
# origin_lat = 22.9974896667  # 緯度
# origin_lon = 120.2216983333  # 經度
# origin_alt = 51.6  # 高度 (假設海平面)
# origin_lat =  24.618989734 # 緯度 moustain test
# origin_lon = 121.286728072  # 經度
# origin_alt = 878.0663  # 高度 (假設海平面)
# origin_lat =  24.6189896667 # 緯度 moustain man test fix
# origin_lon = 121.2867286667  # 經度
# origin_alt = 861  # 高度 (假設海平面)
# origin_lat = 24.618954563 # 緯度 moustain
# origin_lon = 121.286754547  # 經度
# origin_alt = 869.4737  # 高度 (假設海平面)
origin_lat = 24.6190013333 # 緯度 moustain 5c
origin_lon = 121.2869091667  # 經度
origin_alt = 819.8  # 高度 (假設海平面)

current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
print("current time :", current_datetime)
log_folder = r'C:\Users\sgrc-325\Desktop\py\log'
# log_folder = r'C:\Users\弘銘\Desktop\WFH\git\log'
log_filename = f'logger_PC_{current_datetime}.csv'
log_filepath = os.path.join(log_folder, log_filename)

if not os.path.exists(log_folder):
    os.makedirs(log_folder)

print('Waiting for connection...')
log = open(log_filepath, 'w+', encoding="utf8")

# 將經緯度轉換為 3D 笛卡爾座標
def lat_lon_to_cartesian(lat, lon, alt):
    R = 6371000 + alt  # 地球半徑加上高度（單位：公尺）
    phi = math.radians(lat)
    theta = math.radians(lon)
    x = R * math.cos(phi) * math.cos(theta)
    y = R * math.cos(phi) * math.sin(theta)
    z = R * math.sin(phi)
    return x, y, z


# 計算兩點之間的 3D 距離
def calculate_3d_distance(x1, y1, z1, x2, y2, z2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)

# Initialize plot
plt.ion()
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
x_data = []
y_data = []
z_data = []

origin_x, origin_y, origin_z = lat_lon_to_cartesian(origin_lat, origin_lon, origin_alt)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()

    conn, address = s.accept()
    print(f"Connection from {address} has been established.")
    
    full_msg = ''
    new_msg = True
    while True:
        msg = conn.recv(1024)
        full_msg = msg.decode("utf-8")

        if len(full_msg) < 10:
            new_msg = False

        # Extract latitude, longitude, and altitude from the message
        parts = full_msg.split('\t')
        if len(parts) > 8:
            try:
                lat = float(parts[5])
                lon = float(parts[6])
                alt = float(parts[7])  # 假設訊息的第 9 個部分是高度
                x, y, z = lat_lon_to_cartesian(lat, lon, alt)
                
                distance = calculate_3d_distance(origin_x, origin_y, origin_z, x, y, z)
                
                x_data.append(x)
                y_data.append(y)
                z_data.append(z)
                
                # Update 3D plot
                ax.clear()
                ax.scatter(x_data, y_data, z_data, c='blue', marker='.')
                ax.set_xlabel('X (meters)')
                ax.set_ylabel('Y (meters)')
                ax.set_zlabel('Z (meters)')
                ax.set_title(f'3D Distance from Origin: {distance:.2f} meters')
                
                # 顯示當前的 x, y, z 座標
                ax.text2D(0.05, 0.95, f'x: {origin_x-x:.2f} m, y: {origin_y-y:.2f} m, z: {origin_z-z:.2f} m',
                          transform=ax.transAxes)
                
                plt.draw()
                plt.pause(0.01)
                
                # Log the message
                log.write(full_msg)
                log.flush()
                clear_output(wait=True)
                print(full_msg, end='')
#                 print(f'Latitude: {lat}, Longitude: {lon}, Altitude: {alt}')
#                 print(f'X: {origin_x-x:.2f} m, Y: {origin_y-y:.2f} m, Z: {origin_z-z:.2f} m')

            except ValueError:
                # Handle any value conversion errors
                pass

log.close()
conn.close()


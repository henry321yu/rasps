import socket
from time import sleep, strftime, time
import os
from IPython.display import clear_output
from datetime import datetime
import matplotlib.pyplot as plt

HEADERSIZE = 10

# 設定伺服器的 IP 和端口
# HOST = "104.116.45.14"  # office pc
# HOST = "104.116.45.98"  # fly pc
# HOST = "0.0.0.0"  # my pc
HOST = "140.116.45.26"  # 替換為伺服器的 IP 地址
PORT = 5566

current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
print("current time :", current_datetime)
log_folder = r'C:\Users\sgrc-325\Desktop\py\log'
# log_folder = r'C:\Users\弘銘\Desktop\WFH\git\log'
log_filename = f'logger_PC_{current_datetime}.csv'
log_filepath = os.path.join(log_folder, log_filename)

if not os.path.exists(log_folder):
    os.makedirs(log_folder)

print('Attempting to connect to server...')
log = open(log_filepath, 'w+', encoding="utf8")

# Initialize plot
plt.ion()
fig, ax = plt.subplots()
x_data = []
y_data = []

# 創建與伺服器的 TCP/IP 連接
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    try:
        s.connect((HOST, PORT))
        print(f"Connected to server {HOST}:{PORT}.")
    except socket.error as e:
        print(f"Error connecting to server: {e}")
        exit(1)
    
    full_msg = ''
    while True:
        msg = s.recv(1024)
        full_msg = msg.decode("utf-8")

        if len(full_msg) < 10:
#             print("Incomplete message received.")
            continue

        # 解析接收到的消息，提取經緯度信息
        parts = full_msg.split('\t')
        if len(parts) > 8:
            try:
                lat = float(parts[6])
                lon = float(parts[7])
                x_data.append(lon)
                y_data.append(lat)
                
                # 更新圖表
                ax.clear()
                ax.scatter(x_data, y_data, c='blue', marker='o')
                ax.set_xlabel('Longitude')
                ax.set_ylabel('Latitude')
                ax.set_title('GPS Coordinates')
                plt.draw()
                plt.pause(0.01)
                
                # 記錄消息
                log.write(full_msg)
                clear_output(wait=True)
                print(full_msg, end='')
            except ValueError:
                # 處理數值轉換錯誤
                pass

    log.close()
    s.close()

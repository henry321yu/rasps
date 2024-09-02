import time    #發射端
import socket
from datetime import datetime

# 設定伺服器的 IP 和端口
# HOST = "140.116.45.98"  # office pc
HOST = "140.116.45.26"  # rasp office wifi
# HOST = "192.168.0.116"  # 本機 IP 地址
PORT = 5566       # 任意非特權端口

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

print(f"Connecting {HOST}:{PORT}...")
s = connect_to_server()
print('Connected!')
while True:
    try:
        data = s.recv(1024)  # 接收數據
        data=data.decode("utf-8")
        if not data:
            break
        print(f"Received: {data}")
    except (socket.error, BrokenPipeError) as e:
        print(f"Network error while sending data: {e}. Reconnecting...")
        s.close()
        s = connect_to_server()        


import time    #接收端
import socket
from datetime import datetime

# 設定伺服器的 IP 和端口
# HOST = "140.116.45.98"  # office pc
# HOST = "140.116.45.14"  # office fly
HOST = "140.116.45.26"  # rasp office wifi
# HOST = "192.168.0.157"  # fly rasp office wifi
# HOST = "192.168.0.116"  # rasp 4g
# HOST = "2001:b400:e7d5:83bc:ec26:bc4:bd57:c271"  # rasp 4g
# HOST = "100.107.135.29"  # rasp 4g
# HOST = "42.75.39.28"  # rasp 4g

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


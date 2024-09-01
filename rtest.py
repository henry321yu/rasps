import socket

# 設定伺服器的 IP 和端口
HOST = "104.116.45.14"  # 伺服器的本機 IP 地址
PORT = 5566        # 伺服器的端口

# 創建一個 TCP/IP socket
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))  # 連接到伺服器
    s.sendall(b'Hello, server')  # 發送消息
    data = s.recv(1024)  # 接收伺服器的回應

print(f"Received from server: {data.decode()}")

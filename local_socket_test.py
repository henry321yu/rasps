import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# 目標是本機 127.0.0.1 port 2370
sock.sendto(b'test message', ('127.0.0.1', 2370))

print("已發送一個測試封包")

import socket
import time

LIDAR_IP = ""
LIDAR_PORT = 2368

# 多個遠端 PC 的 IP 與 port 組成的列表
REMOTE_PC_LIST = [
    ('26.208.29.50', 2368),
    ('26.214.58.255', 2368),
    ('26.174.179.211', 2368),
    ('26.7.59.242', 2368),
    # 加入更多遠端 PC...
]

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((LIDAR_IP, LIDAR_PORT))

packet_count = 0
total_bytes_sent = 0
start_time = time.time()

while True:
    data, addr = sock.recvfrom(1500)
    
    for remote_ip, remote_port in REMOTE_PC_LIST:
        sent_bytes = sock.sendto(data, (remote_ip, remote_port))
        total_bytes_sent += sent_bytes  # 每次傳送成功回傳的 byte 數

    packet_count += 1

    # 每秒更新一次顯示
    if time.time() - start_time > 1:
        total_mb = total_bytes_sent / (1024 * 1024)
        print(f"封包數：{packet_count}  |  傳送：{total_mb:.2f} MB", end='\n')
        start_time = time.time()
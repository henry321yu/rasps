import socket
import time

LIDAR_IP = ""  # 空字串表示綁定所有介面
LIDAR_PORT = 2368

# 多個遠端 PC 的 IP 與 port 組成的列表
REMOTE_PC_LIST = [
    ('10.241.0.114',2368),
    ('10.241.215.99', 2368),
    ('10.241.180.148', 2368),
    ('10.241.199.211', 2368),
    # 加入更多遠端 PC...
]


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((LIDAR_IP, LIDAR_PORT))

packet_count = 0
total_bytes_sent = 0
sent_bytes_per_pc = {ip: 0 for ip, _ in REMOTE_PC_LIST}

last_display_time = time.time()

def display_status():
    print(f"\n總封包數：{packet_count}")
    print(f"總傳輸量：{total_bytes_sent / (1024 * 1024):.2f} MB")
    print("各電腦傳輸量：")
    for ip, byte_count in sent_bytes_per_pc.items():
        print(f"  {ip} ： {byte_count / (1024 * 1024):.2f} MB")
    print("-" * 40)

while True:
    data, addr = sock.recvfrom(1500)
    
    for remote_ip, remote_port in REMOTE_PC_LIST:
        sent_bytes = sock.sendto(data, (remote_ip, remote_port))
        total_bytes_sent += sent_bytes
        sent_bytes_per_pc[remote_ip] += sent_bytes

    packet_count += 1

    # 每 2 秒更新畫面
    if time.time() - last_display_time >= 2:
        display_status()
        last_display_time = time.time()

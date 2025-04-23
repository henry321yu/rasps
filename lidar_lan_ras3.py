import socket
import time
import os
import platform
import threading

LIDAR_IP = ""  # 空字串表示綁定所有介面
LIDAR_PORT = 2368

REMOTE_PC_LIST = [
    ('10.241.0.114', 2368),
    ('10.241.215.99', 2368),
    ('10.241.180.148', 2368),
    ('10.241.199.211', 2368),
    # 更多 IP...
]

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((LIDAR_IP, LIDAR_PORT))

packet_count = 0
total_bytes_sent = 0
sent_bytes_per_pc = {ip: 0 for ip, _ in REMOTE_PC_LIST}
online_status = {ip: False for ip, _ in REMOTE_PC_LIST}

last_display_time = time.time()

# 清除終端畫面
def clear_screen():
    os.system('cls' if platform.system().lower() == 'windows' else 'clear')

# 每台 IP 是否開機（用 ping）
def ping(ip):
    param = "-n" if platform.system().lower() == "windows" else "-c"
    result = os.system(f"ping {param} 1 {ip} > /dev/null 2>&1")
    return result == 0

# 背景執行的 ping 檢查執行緒
def ping_checker():
    while True:
        for ip, _ in REMOTE_PC_LIST:
            online_status[ip] = ping(ip)
        time.sleep(5)

# 顯示統計資訊
def display_status():
    clear_screen()
    print(f"總封包數：{packet_count}")
    print(f"總傳輸量：{total_bytes_sent / (1024 * 1024):.2f} MB")
    print("各電腦傳輸量與狀態：")
    for ip in sent_bytes_per_pc:
        status = "online" if online_status[ip] else "offline"
        mb = sent_bytes_per_pc[ip] / (1024 * 1024)
        print(f"  {ip} ： {mb:.2f} MB  {status}")
    print("-" * 40)

# 啟動背景 ping 檢查執行緒
threading.Thread(target=ping_checker, daemon=True).start()

# 主迴圈：接收封包並轉發
while True:
    try:
        data, addr = sock.recvfrom(1500)
    except Exception:
        continue

    for remote_ip, remote_port in REMOTE_PC_LIST:
        if not online_status[remote_ip]:
            continue  # 跳過沒開機的

        try:
            sent_bytes = sock.sendto(data, (remote_ip, remote_port))
            total_bytes_sent += sent_bytes
            sent_bytes_per_pc[remote_ip] += sent_bytes
        except Exception:
            pass  # 傳送失敗就略過，不影響主程式

    packet_count += 1

    if time.time() - last_display_time >= 1:
        display_status()
        last_display_time = time.time()

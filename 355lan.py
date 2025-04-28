import socket
import time
import os
import platform
import threading
import smbus2

# ADXL355 Register Map
TEMP2 = 0x06
XDATA3 = 0x08
YDATA3 = 0x0B
ZDATA3 = 0x0E
RESET = 0x2F
POWER_CTL = 0x2D
RANGE = 0x2C
SELF_TEST = 0x2E

# 初始化
bus = smbus2.SMBus(1)
Device_Address = 0x1D  # ADXL355 I2C位址

def setup_355_m():
    write_355(RESET, 0x52)
    time.sleep(0.1)
    write_355(POWER_CTL, 0x00)
    time.sleep(0.03)
    write_355(RANGE, 0x01)
    time.sleep(0.03)
    write_355(SELF_TEST, 0x00)
    time.sleep(0.1)

def write_355(addr, value):
    bus.write_byte_data(Device_Address, addr, value)

def read_355_m():
    var = bus.read_i2c_block_data(Device_Address, TEMP2, 11)
    
    ax = (var[2] << 12 | var[3] << 4 | var[4] >> 4)
    ay = (var[5] << 12 | var[6] << 4 | var[7] >> 4)
    az = (var[8] << 12 | var[9] << 4 | var[10] >> 4)
    
    rangee = 0x3E800  # 2g範圍
    
    if ax > 0x80000:
        ax = ax - 0x100000
    ax = ax / rangee
    
    if ay > 0x80000:
        ay = ay - 0x100000
    ay = ay / rangee
    
    if az > 0x80000:
        az = az - 0x100000
    az = az / rangee
    
    temp_raw = (var[0] << 8 | var[1])
    temp = ((1852 - temp_raw) / 9.05) + 27.2  # 溫度校正

    return ax, ay, az, temp

# --- 下面是Socket傳送相關 ---

ACCPORT = 2370

REMOTE_PC_LIST = [
    ('10.241.0.114', ACCPORT),
    ('10.241.215.99', ACCPORT),
    ('10.241.180.148', ACCPORT),
    ('10.241.199.211', ACCPORT),
    # 更多 IP...
]

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

packet_count = 0
total_bytes_sent = 0
sent_bytes_per_pc = {ip: 0 for ip, _ in REMOTE_PC_LIST}
online_status = {ip: False for ip, _ in REMOTE_PC_LIST}

last_display_time = time.time()

def clear_screen():
    os.system('cls' if platform.system().lower() == 'windows' else 'clear')

def ping(ip):
    param = "-n" if platform.system().lower() == "windows" else "-c"
    result = os.system(f"ping {param} 1 {ip} > /dev/null 2>&1")
    return result == 0

def ping_checker():
    while True:
        for ip, _ in REMOTE_PC_LIST:
            online_status[ip] = ping(ip)
        time.sleep(5)

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

# 啟動背景ping檢查線程
threading.Thread(target=ping_checker, daemon=True).start()

# 設定 ADXL355
setup_355_m()

# 主迴圈：讀ADXL355並用UDP發送
while True:
    ax, ay, az, temp = read_355_m()

    # 封裝成字串
    message = f"ADXL355,{ax:.6f},{ay:.6f},{az:.6f},{temp:.2f}"
    data = message.encode('utf-8')

    for remote_ip, remote_port in REMOTE_PC_LIST:
        if not online_status[remote_ip]:
            continue

        try:
            sent_bytes = sock.sendto(data, (remote_ip, remote_port))
            total_bytes_sent += sent_bytes
            sent_bytes_per_pc[remote_ip] += sent_bytes
        except Exception as e:
            pass  # 傳送失敗就略過，不影響主程式

    packet_count += 1

    if time.time() - last_display_time >= 1:
        display_status()
        last_display_time = time.time()

    time.sleep(0.01)  # 每10ms送一次

import socket
import struct
import math
import time
import threading
import queue
from datetime import datetime

# LiDAR 設定
LOCAL_IP = "0.0.0.0"
UDP_PORT = 2368
PACKET_SIZE = 1212
DISTANCE_RESOLUTION = 0.004

VERTICAL_ANGLES = [
    -15, 1, -13, 3, -11, 5, -9, 7,
    -7, 9, -5, 11, -3, 13, -1, 15
]

data_list = []
intensity_list = []
i_max_points = 16000  # 20hz

# 建立 Lidar UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((LOCAL_IP, UDP_PORT))
print(f"Listening on Lidar UDP port {UDP_PORT}...")

# 建立 ADXL355 UDP socket
sock_recv_355 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_recv_355.bind((LOCAL_IP, 2370))
print(f"Listening on ADXL355 UDP port {2370}...")

# 建立 2369 UDP socket
sock_recv_2369 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_recv_2369.bind((LOCAL_IP, 2369))
print(f"Listening on 2369 UDP port {2369}...")

time.sleep(1) # waiting for all UDP

# 新增全局變數
ax = ay = az = tem = 0.0  # 用來存放接收到的加速度和溫度數據
printclock = board2_temp = 0

# queue
packet_queue = queue.Queue(maxsize=i_max_points)
packet_queue_full = 0

frame_count = dframe_count = 0
start_time_ns = time.perf_counter_ns()

def parse_packet(data):
    blocks = 12
    channels = 16
    results = []

    for block_idx in range(blocks):
        base = 100 * block_idx
        if data[base:base+2] != b'\xFF\xEE':
            continue
        azimuth = struct.unpack_from("<H", data, base + 2)[0] / 100.0
        for firing in range(2):
            for ch in range(channels):
                idx = firing * channels + ch
                offset = base + 4 + idx * 3
                distance_raw = struct.unpack_from("<H", data, offset)[0]
                intensity = data[offset + 2]
                distance = distance_raw * DISTANCE_RESOLUTION
                # if distance == 0:
                #     continue
                vert_angle = VERTICAL_ANGLES[ch]

                results.append((vert_angle, azimuth, distance, intensity))
    return results

def receiver_thread(sock):
    global packet_queue_full
    while True:
        data, _ = sock.recvfrom(PACKET_SIZE)
        if len(data) == PACKET_SIZE:
            try:
                packet_queue.put_nowait(data)
            except queue.Full:                
                packet_queue_full = 1
                pass

def pointcloud_updater():
    global start_time_ns, gotnp, i_max_points, frame_count, dframe_count, ax, ay, az, tem, printclock, board2_temp

    last_time_ns = time.perf_counter_ns()  # 加入這行：記錄上一次的時間

    while True:
        data = packet_queue.get()
        points = parse_packet(data)
        if len(points) > 0:
            data_list.extend(points)

        if len(data_list) >= i_max_points:
            current_time = datetime.now().strftime("%H:%M:%S.%f")[:-4]
            current_time_ns = time.perf_counter_ns()
            elapsed_ns_total = current_time_ns - start_time_ns
            elapsed_ns_recent = current_time_ns - last_time_ns  # 重點：這是最近兩次間的差
            elapsed_s_recent = elapsed_ns_recent / 1e9
            elapsed_s_total = elapsed_ns_total / 1e9

            # 更新 frame count
            frame_count += len(data_list)
            dframe_count += 1

            # 重點：僅使用最近一次的資料計算頻率
            dfrequency = 1.0 / elapsed_s_recent if elapsed_s_recent > 0 else 0.0
            frequency = len(data_list) / elapsed_s_recent / 1000 if elapsed_s_recent > 0 else 0.0

            last_time_ns = current_time_ns  # 更新時間基準點

            for vert_angle, azimuth, distance, intensity in data_list:
                # 印出 LiDAR 資料以及接收到的加速度和溫度數據
                # print(f"{current_time}, {elapsed_s:.3f}s, {vert_angle}, {azimuth:.2f}, {distance:.2f}, {ax}, {ay}, {az}, {tem}°C, Points:{len(data_list)}, {frequency:.2f} kHz, {dfrequency:.2f} Hz")
                if elapsed_s_total > printclock:
                    printclock = printclock + 0.5
                    print(f"{current_time}, {elapsed_s_total:.3f}s, {vert_angle}, {azimuth:.2f}, {distance:.2f}, {board2_temp:.2f}°C, {ax}, {ay}, {az}, {tem}°C, Points:{len(data_list)}, {frequency:.2f} kHz, {dfrequency:.2f} Hz")

            data_list.clear()
            intensity_list.clear()


def monitor():
    global packet_queue_full
    while True:        
        if packet_queue_full == 1:
            print(f"[Monitor] packet_queue is full!!")
        else:            
            print(f"[Monitor] packet_queue size: {packet_queue.qsize()}")
        packet_queue_full = 0
        time.sleep(2)

def get_355():
    global ax, ay, az, tem
    while True:
        try:
            data, addr = sock_recv_355.recvfrom(1024)  # 最多收1024 bytes
            message = data.decode('utf-8')

            # 分割資料
            parts = message.split(',')
            if len(parts) == 5:
                ID = parts[0]
                ax = float(parts[1])
                ay = float(parts[2])
                az = float(parts[3])
                tem = float(parts[4])
        except Exception as e:
            pass

def get_2369():
    global board2_temp
    while True:
        try:
            data, addr = sock_recv_2369.recvfrom(1500)  # 最多收1024 bytes
            EXPECTED_HEADER = b'\xA5\xFF\x00\x5A\x11\x11\x55\x55'
            EXPECTED_TAIL = b'\x0F\xF0'

            if len(data) != 1206:
                print("封包長度錯誤:", len(data))
                return

            if not data.startswith(EXPECTED_HEADER) or not data.endswith(EXPECTED_TAIL):
                print("封包開頭或結尾錯誤")
                return

            # 溫度（以 0.01°C 計算後再乘 3，可能是補償係數）
            temp_raw = struct.unpack_from('>h', data, 80)[0]
            board2_temp = (temp_raw / 100.0) * 6.03226 - 48.84387
            if board2_temp < 25:
                board2_temp = 25
        except Exception as e:
            pass


def main():
    threading.Thread(target=get_355, daemon=True).start()
    threading.Thread(target=get_2369, daemon=True).start()
    threading.Thread(target=receiver_thread, args=(sock,), daemon=True).start()
    threading.Thread(target=pointcloud_updater, daemon=True).start()
    # threading.Thread(target=monitor, daemon=True).start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()

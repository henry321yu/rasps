
# ========= 使用者可自訂 =========
LIDAR_BUFFER_SECONDS = 20
IMU_SAVE_INTERVAL = 600
IMU_LOG_FOLDER = "lidar_log"
T7 = 10

import cv2
import time
import socket
import os
import platform
import threading
import smbus2
from datetime import datetime
import RPi.GPIO as GPIO
from collections import deque

# ========= Relay 設定 =========
RELAY_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)
GPIO.output(RELAY_PIN, GPIO.HIGH)

# ========= ADXL355 設定 =========
TEMP2, XDATA3, YDATA3, ZDATA3 = 0x06, 0x08, 0x0B, 0x0E
RESET, POWER_CTL, RANGE, SELF_TEST = 0x2F, 0x2D, 0x2C, 0x2E
bus = smbus2.SMBus(1)
ADXL355_ADDR = 0x1D

def setup_adxl355():
    bus.write_byte_data(ADXL355_ADDR, RESET, 0x52)
    time.sleep(0.1)
    bus.write_byte_data(ADXL355_ADDR, POWER_CTL, 0x00)
    bus.write_byte_data(ADXL355_ADDR, RANGE, 0x01)
    bus.write_byte_data(ADXL355_ADDR, SELF_TEST, 0x00)
    time.sleep(0.1)

def read_adxl355():
    data = bus.read_i2c_block_data(ADXL355_ADDR, TEMP2, 11)
    ax = ((data[2] << 12) | (data[3] << 4) | (data[4] >> 4)) & 0xFFFFF
    ay = ((data[5] << 12) | (data[6] << 4) | (data[7] >> 4)) & 0xFFFFF
    az = ((data[8] << 12) | (data[9] << 4) | (data[10] >> 4)) & 0xFFFFF
    ax = ax - 0x100000 if ax > 0x80000 else ax
    ay = ay - 0x100000 if ay > 0x80000 else ay
    az = az - 0x100000 if az > 0x80000 else az
    temp_raw = (data[0] << 8) | data[1]
    temp = ((1852 - temp_raw) / 9.05) + 27.2
    return ax / 0x3E800, ay / 0x3E800, az / 0x3E800, temp

# ========= 網路與設備清單 =========
REMOTE_PC_LIST = [
    ('10.241.0.114', 0), # my office
    ('10.241.215.99', 0),  # dell
    ('10.241.180.148', 0), # my pc
    ('10.241.199.211', 0), # fly office
    ('10.241.183.64', 0), # ipc
    ('10.241.66.133', 0), # broken
    ('10.241.135.1', 0), # my new office
]

ADXL_PORT = 2370
IMAGE_PORT = 2385
PIXEL_PORT = 2386
LIDAR1_PORT = 2368
LIDAR2_PORT = 2369
RELAY_PORT = 2371

sock_adxl = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_img = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_pixel = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_lidar1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_lidar2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_lidar1.bind(("", LIDAR1_PORT))
sock_lidar2.bind(("", LIDAR2_PORT))

# ========= 狀態變數 =========
online_status = {ip: True for ip, _ in REMOTE_PC_LIST}
lidar_buffer = deque()
buffer_lock = threading.Lock()
last_trigger_time = 0
trigger_active = False
avg20 = 100
avg30 = 100
avg40 = 100
avg50 = 100
last_avg30 = None  
last_avg20 = None
trigger_pending = False

adxl_sent = 0
img_sent = 0
pixel_sent = 0
lidar1_sent = 0
lidar2_sent = 0

imu_log = []
imu_log_lock = threading.Lock()

def ping(ip):
    param = "-n" if platform.system().lower() == "windows" else "-c"
    return os.system(f"ping {param} 1 {ip} > /dev/null 2>&1") == 0

def ping_checker():
    while True:
        for ip, _ in REMOTE_PC_LIST:
            online_status[ip] = ping(ip)
        time.sleep(5)

def save_imu_log_periodically():
    while True:
        time.sleep(IMU_SAVE_INTERVAL)
        now = datetime.now()
        filename = now.strftime("imu_%Y%m%d_%H%M%S.csv")
        os.makedirs(IMU_LOG_FOLDER, exist_ok=True)
        filepath = os.path.join(IMU_LOG_FOLDER, filename)
        with imu_log_lock:
            if imu_log:
                with open(filepath, "w") as f:
                    f.write("timestamp,ax,ay,az,temp\n")
                    f.writelines(imu_log)
                print(f"💾 已儲存 {len(imu_log)} 筆 IMU 資料到 {filepath}")
                imu_log.clear()

def send_adxl355():
    global adxl_sent
    while True:
        ax, ay, az, temp = read_adxl355()
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        message = f"ADXL355,{ax:.6f},{ay:.6f},{az:.6f},{temp:.2f}"
        with imu_log_lock:
            imu_log.append(f"{ts},{ax:.6f},{ay:.6f},{az:.6f},{temp:.2f}\n")
        for ip, _ in REMOTE_PC_LIST:
            if online_status[ip]:
                sock_adxl.sendto(message.encode(), (ip, ADXL_PORT))
                adxl_sent += 1
        time.sleep(0.01)

def send_camera():
    global img_sent, pixel_sent, avg20, avg30, avg40, avg50
    cap = None
    frame_count = 0
    interval = 0.5
    while True:
        if cap is None or not cap.isOpened():
            cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
            time.sleep(2)
            continue
        ret, frame = cap.read()
        if not ret:
            cap.release()
            cap = None
            continue
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        resized = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        if gray.shape[0] > 50 and gray.shape[1] > 100:
            avg20 = int(gray[20, 50:100].mean())
            avg30 = int(gray[30, 50:100].mean())
            avg40 = int(gray[40, 50:100].mean())
            avg50 = int(gray[50, 50:100].mean())
        else:
            avg20 = avg30 = avg40 = avg50 = 0
        pixel_msg = f"{ts},{avg20},{avg30},{avg40},{avg50}"
        for ip, _ in REMOTE_PC_LIST:
            if online_status[ip]:
                sock_pixel.sendto(pixel_msg.encode(), (ip, PIXEL_PORT))
                pixel_sent += 1
        if frame_count % 2 == 0:
            success, jpeg = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
            if success and len(jpeg) < 60000:
                for ip, _ in REMOTE_PC_LIST:
                    if online_status[ip]:
                        sock_img.sendto(jpeg.tobytes(), (ip, IMAGE_PORT))
                        img_sent += 1
        frame_count += 1
        time.sleep(interval)


def save_lidar_buffer():
    now = datetime.now()
    filename = now.strftime("lidar1_%Y%m%d_%H%M%S.bin")
    os.makedirs("lidar_log", exist_ok=True)
    filepath = os.path.join("lidar_log", filename)
    print(f"💾 正在儲存檔案: {filepath}")
    with open(filepath, "wb") as f:
        with buffer_lock:
            for _, pkt in lidar_buffer:
                f.write(pkt)
    print(f"✅ 已儲存 {len(lidar_buffer)} 筆資料")

def lidar1():
    global lidar1_sent, trigger_active, last_trigger_time
    global last_avg20, last_avg30, trigger_pending

    while True:
        data, _ = sock_lidar1.recvfrom(1500)
        timestamp = time.time()
        with buffer_lock:
            lidar_buffer.append((timestamp, data))
            while lidar_buffer and (timestamp - lidar_buffer[0][0]) > LIDAR_BUFFER_SECONDS:
                lidar_buffer.popleft()
        for ip, _ in REMOTE_PC_LIST:
            if online_status[ip]:
                sock_lidar1.sendto(data, (ip, LIDAR1_PORT))
                lidar1_sent += 1

        try:
            current_avg20 = avg20
            current_avg30 = avg30
            if last_avg20 is not None and last_avg30 is not None and not trigger_pending:
                if (last_avg20 - current_avg20 > 50) and (last_avg30 - current_avg30 > 50):
                    def delayed_trigger():
                        global trigger_active, last_trigger_time, trigger_pending
                        time.sleep(T7)
                        now = time.time()
                        if now - last_trigger_time > 15:
                            print(f"🚨 avg20/avg30 急降：{last_avg20}/{last_avg30} → {current_avg20}/{current_avg30}，T7 秒後觸發")
                            trigger_active = True
                            last_trigger_time = now
                            threading.Thread(target=save_lidar_buffer, daemon=True).start()
                        trigger_pending = False
                    trigger_pending = True
                    threading.Thread(target=delayed_trigger, daemon=True).start()
            last_avg20 = current_avg20
            last_avg30 = current_avg30
        except Exception as e:
            print(f"[ERROR] avg trigger 判斷錯誤: {e}")

        if avg20 >= 50:
            trigger_active = False


def lidar2():
    global lidar2_sent
    while True:
        data, _ = sock_lidar2.recvfrom(1500)
        for ip, _ in REMOTE_PC_LIST:
            if online_status[ip]:
                sock_lidar2.sendto(data, (ip, LIDAR2_PORT))
                lidar2_sent += 1

def print_status():
    while True:
        os.system('cls' if platform.system().lower() == 'windows' else 'clear')
        print(f"  avg20 = {avg20} | 觸發中: {'是' if trigger_active else '否'}")
        print(f"  ADXL355: {adxl_sent} | 圖像: {img_sent} | 像素: {pixel_sent}")
        print(f"  LiDAR1: {lidar1_sent} | LiDAR2: {lidar2_sent}")
        for ip, _ in REMOTE_PC_LIST:
            status = "Online" if online_status[ip] else "Offline"
            print(f"  {ip} : {status}")
        time.sleep(10)

def relay_control_listener():
    relay_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    relay_sock.bind(('', RELAY_PORT))
    while True:
        data, addr = relay_sock.recvfrom(1024)
        command = data.decode().strip().upper()
        if command == "ON":
            GPIO.output(RELAY_PIN, GPIO.HIGH)
        elif command == "OFF":
            GPIO.output(RELAY_PIN, GPIO.LOW)

if __name__ == "__main__":
    time.sleep(10)
    setup_adxl355()
    threading.Thread(target=ping_checker, daemon=True).start()
    threading.Thread(target=send_adxl355, daemon=True).start()
    threading.Thread(target=save_imu_log_periodically, daemon=True).start()
    threading.Thread(target=send_camera, daemon=True).start()
    threading.Thread(target=lidar1, daemon=True).start()
    threading.Thread(target=lidar2, daemon=True).start()
    threading.Thread(target=print_status, daemon=True).start()
    threading.Thread(target=relay_control_listener, daemon=True).start()
    print("🟢 系統啟動中... Ctrl+C 可中斷")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        sock_adxl.close()
        sock_img.close()
        sock_pixel.close()
        sock_lidar1.close()
        sock_lidar2.close()
        print("🔴 手動中斷")

import cv2
import time
import socket
import os
import platform
import threading
import smbus2
from datetime import datetime
import pyaudio  # 用於麥克風收音

# install list:
# sudo apt install -y python3-opencv python3-pyaudio
# sudo apt install -y portaudio19-dev
# pip3 install smbus2
# python3 -m pip install flask numpy waitress --break-system-packages

# ========= MPU6050 設定 (雙模組) =========
MPU6050_ADDR_1 = 0x68  # AD0 接 GND
MPU6050_ADDR_2 = 0x69  # AD0 接 3.3V

# MPU6050 Registers
PWR_MGMT_1   = 0x6B
ACCEL_XOUT_H = 0x3B

bus = smbus2.SMBus(1)

def setup_mpu6050():
    # 喚醒兩顆 MPU6050 (寫入 0 至電源管理暫存器)
    bus.write_byte_data(MPU6050_ADDR_1, PWR_MGMT_1, 0x00)
    bus.write_byte_data(MPU6050_ADDR_2, PWR_MGMT_1, 0x00)
    time.sleep(0.1)

def read_mpu6050_single(addr):
    # 一次讀取 6 個位元組: 加速度 3 軸 (6 bytes)，略過溫度
    data = bus.read_i2c_block_data(addr, ACCEL_XOUT_H, 6)
    
    def convert(high, low):
        val = (high << 8) | low
        return val - 65536 if val >= 32768 else val
        
    # MPU6050 預設範圍是 ±2g，靈敏度為 16384 LSB/g
    ax = convert(data[0], data[1]) / 16384.0
    ay = convert(data[2], data[3]) / 16384.0
    az = convert(data[4], data[5]) / 16384.0
    
    return ax, ay, az

# ========= 網路與設備清單 =========
REMOTE_PC_LIST = [
    ('127.0.0.1', 0), # server (請依據需求改成你的 Server IP)
]

MPU_PORT = 2870
IMAGE_PORT = 2885
PIXEL_PORT = 2886
AUDIO_PORT = 2890
CONTROL_PORT = 2895 # [新增] 接收伺服器控制指令 PORT

sock_mpu = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_img = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_pixel = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_audio = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_control = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # [新增] 控制接收
sock_control.bind(("0.0.0.0", CONTROL_PORT))

# ========= 狀態變數 =========
online_status = {ip: True for ip, _ in REMOTE_PC_LIST}
avg20 = avg30 = avg40 = avg50 = 100
mpu_sent = img_sent = pixel_sent = audio_sent = 0
image_quality = 40 # [新增] 預設影像畫質

def ping(ip):
    param = "-n" if platform.system().lower() == "windows" else "-c"
    return os.system(f"ping {param} 1 {ip} > /dev/null 2>&1") == 0

def ping_checker():
    while True:
        for ip, _ in REMOTE_PC_LIST:
            online_status[ip] = ping(ip)
        time.sleep(5)

# [新增] 監聽來自伺服器的畫質變更指令
def control_receiver():
    global image_quality
    while True:
        try:
            data, addr = sock_control.recvfrom(1024)
            msg = data.decode("utf-8")
            if msg.startswith("QUALITY:"):
                new_q = int(msg.split(":")[1])
                image_quality = new_q
        except Exception as e:
            pass

def send_mpu6050():
    global mpu_sent
    last_az1 = None
    PREFIX = "MPU6050,"
    while True:
        try:
            # 分別讀取兩顆感測器的資料
            ax1, ay1, az1 = read_mpu6050_single(MPU6050_ADDR_1)
            ax2, ay2, az2 = read_mpu6050_single(MPU6050_ADDR_2)
            
            # 利用第一顆的 az 軸作為資料變動的簡單過濾
            if az1 == last_az1:
                continue
            last_az1 = az1
            
            # 將 6 個軸的資料組裝發送
            message = PREFIX + "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f" % (ax1, ay1, az1, ax2, ay2, az2)
            
            for ip, _ in REMOTE_PC_LIST:
                if online_status[ip]:
                    sock_mpu.sendto(message.encode(), (ip, MPU_PORT))
                    mpu_sent += 1
        except Exception:
            pass # 忽略 I2C 偶發的錯誤
        time.sleep(0.0005)

def send_camera():
    global img_sent, pixel_sent, avg20, avg30, avg40, avg50, image_quality
    cap = None
    interval = 0.05
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
        overlay = frame.copy()
        cv2.rectangle(overlay, (5, 3), (234, 25), (0, 0, 0), -1) # 黑塊長度 225給.00  232給.000
        cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)
        cv2.putText(frame, ts, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        
        resized = cv2.resize(frame, (0, 0), fx=1, fy=1)
        
        # [修改] 使用全域變數 image_quality
        success, jpeg = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), image_quality])
        
        if success:
            if len(jpeg) >= 60000:
                # [修改] 低畫質為高畫質 - 20，並確保不小於 0
                low_quality = max(0, image_quality - 20)
                success, jpeg = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), low_quality]) 
            
            if success and len(jpeg) < 60000:
                for ip, _ in REMOTE_PC_LIST:
                    if online_status[ip]:
                        sock_img.sendto(jpeg.tobytes(), (ip, IMAGE_PORT))
                        img_sent += 1
        time.sleep(interval)

def send_audio():
    global audio_sent
    CHUNK = 2048
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000

    while True:
        p = pyaudio.PyAudio()
        stream = None
        try:
            stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
            print("🎙️ 麥克風收音啟動成功 / 已重新連線！")
            
            while True:
                data = stream.read(CHUNK, exception_on_overflow=False)
                
                for ip, _ in REMOTE_PC_LIST:
                    if online_status[ip]:
                        sock_audio.sendto(data, (ip, AUDIO_PORT))
                        audio_sent += 1
                        
        except Exception as e:
            print(f"⚠️ 音訊設備未就緒或已拔除，2秒後重試... (原因: {e})")
            
        finally:
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except:
                    pass
            p.terminate() 
            
        time.sleep(2)

def print_status():
    while True:
        os.system('cls' if platform.system().lower() == 'windows' else 'clear')
        print(f"  avg20 = {avg20}")
        print(f"  MPU6050: {mpu_sent} | 圖像: {img_sent} | 音訊: {audio_sent} | 當前畫質: {image_quality}")
        for ip, _ in REMOTE_PC_LIST:
            status = "Online" if online_status[ip] else "Offline"
            print(f"  {ip} : {status}")
        time.sleep(10)

if __name__ == "__main__":
    time.sleep(10)
    setup_mpu6050()
    threading.Thread(target=ping_checker, daemon=True).start()
    threading.Thread(target=control_receiver, daemon=True).start() # [新增] 啟動控制接收執行緒
    threading.Thread(target=send_mpu6050, daemon=True).start()
    threading.Thread(target=send_camera, daemon=True).start()
    threading.Thread(target=send_audio, daemon=True).start()
    threading.Thread(target=print_status, daemon=True).start()
    
    print("🟢 系統啟動中... Ctrl+C 可中斷")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        sock_mpu.close()
        sock_img.close()
        sock_pixel.close()
        sock_audio.close()
        sock_control.close()
        print("🔴 手動中斷")
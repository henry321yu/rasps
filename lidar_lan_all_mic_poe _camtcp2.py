import cv2
import time
import socket
import os
import platform
import threading
import smbus2
from datetime import datetime
import subprocess 
import struct  # [新增] 用於將影像大小打包成二進制

# ========= 攝影機 RTSP 設定 =========
RTSP_URL = "rtsp://192.168.137.77:554/ch01.264" 

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
    ('127.0.0.1', 0), # server (請依據需求改成你的 Server IP)
]

ADXL_PORT = 2870
IMAGE_PORT = 2885 # 現改為 TCP 使用
PIXEL_PORT = 2886
AUDIO_PORT = 2890  
CONTROL_PORT = 2895 

sock_adxl = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_audio = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  
sock_control = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
sock_control.bind(("0.0.0.0", CONTROL_PORT))

# ========= 狀態變數 =========
online_status = {ip: True for ip, _ in REMOTE_PC_LIST}
avg20 = avg30 = avg40 = avg50 = 100
adxl_sent = img_sent = pixel_sent = audio_sent = 0
image_quality = 70 

def ping(ip):
    param = "-n" if platform.system().lower() == "windows" else "-c"
    return os.system(f"ping {param} 1 {ip} > /dev/null 2>&1") == 0

def ping_checker():
    while True:
        for ip, _ in REMOTE_PC_LIST:
            online_status[ip] = ping(ip)
        time.sleep(5)

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

def send_adxl355():
    global adxl_sent
    last_az = None
    PREFIX = "ADXL355,"
    while True:
        ax, ay, az, temp = read_adxl355()
        if az == last_az:
            continue
        last_az = az
        message = PREFIX + "%.6f,%.6f,%.6f,%.2f" % (ax, ay, az, temp)
        for ip, _ in REMOTE_PC_LIST:
            if online_status[ip]:
                sock_adxl.sendto(message.encode(), (ip, ADXL_PORT))
                adxl_sent += 1
        time.sleep(0.0005)

def send_camera():
    global img_sent, pixel_sent, avg20, avg30, avg40, avg50, image_quality
    cap = None
    interval = 0.05
    tcp_socks = {}  # [新增] 用來管理 TCP 連線

    while True:
        if cap is None or not cap.isOpened():
            cap = cv2.VideoCapture(RTSP_URL)
            time.sleep(2)
            continue
            
        ret, frame = cap.read()
        if not ret:
            print("無法讀取畫面，可能是網路延遲或斷線，嘗試重連...")
            cap.release()
            cap = None
            continue

        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        overlay = frame.copy()
        cv2.rectangle(overlay, (5, 3), (234, 25), (0, 0, 0), -1) 
        cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)
        cv2.putText(frame, ts, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        
        success, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), image_quality])
        
        if success:
            jpeg_bytes = jpeg.tobytes()
            # [新增] 準備 4 bytes 的整數作為封包長度標記
            length_prefix = len(jpeg_bytes).to_bytes(4, byteorder='big')
            packet = length_prefix + jpeg_bytes
            
            for ip, _ in REMOTE_PC_LIST:
                if online_status[ip]:
                    try:
                        # [新增] 若沒有連線則建立 TCP 連線
                        if ip not in tcp_socks:
                            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            s.settimeout(2)  # 避免卡死
                            s.connect((ip, IMAGE_PORT))
                            tcp_socks[ip] = s
                        
                        # 發送：長度 + 影像資料
                        tcp_socks[ip].sendall(packet)
                        img_sent += 1
                    except Exception as e:
                        # 若發送失敗，斷開連線，下次迴圈會重新連線
                        if ip in tcp_socks:
                            tcp_socks[ip].close()
                            del tcp_socks[ip]
                            
        time.sleep(interval)

def send_audio():
    global audio_sent
    CHUNK = 2048  
    while True: 
        process = None
        try:
            command = [
                'ffmpeg',
                '-i', RTSP_URL,
                '-f', 's16le',         
                '-acodec', 'pcm_s16le',
                '-ac', '1',            
                '-ar', '16000',        
                '-vn',                 
                '-sn',                 
                '-loglevel', 'quiet',  
                '-'                    
            ]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("🎙️ RTSP 音訊收音啟動成功 / 已重新連線！")
            
            while True:  
                data = process.stdout.read(CHUNK)
                if not data:
                    print("⚠️ RTSP 音訊流結束或斷線，準備重連...")
                    break 
                
                for ip, _ in REMOTE_PC_LIST:
                    if online_status[ip]:
                        sock_audio.sendto(data, (ip, AUDIO_PORT))
                        audio_sent += 1
                        
        except Exception as e:
            print(f"⚠️ RTSP 音訊讀取失敗，2秒後重試... (原因: {e})")
            
        finally:
            if process:
                process.kill()
                process.wait()
            
        time.sleep(2)

def print_status():
    while True:
        os.system('cls' if platform.system().lower() == 'windows' else 'clear')
        print(f"  avg20 = {avg20}")
        print(f"  ADXL355: {adxl_sent} | 圖像: {img_sent} | 音訊: {audio_sent} | 當前畫質: {image_quality}")
        for ip, _ in REMOTE_PC_LIST:
            status = "Online" if online_status[ip] else "Offline"
            print(f"  {ip} : {status}")
        time.sleep(10)

if __name__ == "__main__":
    time.sleep(10)
    setup_adxl355()
    threading.Thread(target=ping_checker, daemon=True).start()
    threading.Thread(target=control_receiver, daemon=True).start() 
    threading.Thread(target=send_adxl355, daemon=True).start()
    threading.Thread(target=send_camera, daemon=True).start()
    threading.Thread(target=send_audio, daemon=True).start() 
    threading.Thread(target=print_status, daemon=True).start()
    
    print("🟢 系統啟動中... Ctrl+C 可中斷")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        sock_adxl.close()
        sock_audio.close()
        sock_control.close()
        print("🔴 手動中斷")
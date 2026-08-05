import cv2
import time
import socket
import os
import platform
import threading
import smbus2
from datetime import datetime
import pyaudio  # [新增] 用於麥克風收音

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
IMAGE_PORT = 2885
PIXEL_PORT = 2886
AUDIO_PORT = 2890  # [新增] 音訊傳輸 PORT

sock_adxl = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_img = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_pixel = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_audio = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # [新增]

# ========= 狀態變數 =========
online_status = {ip: True for ip, _ in REMOTE_PC_LIST}
avg20 = avg30 = avg40 = avg50 = 100
adxl_sent = img_sent = pixel_sent = audio_sent = 0

def ping(ip):
    param = "-n" if platform.system().lower() == "windows" else "-c"
    return os.system(f"ping {param} 1 {ip} > /dev/null 2>&1") == 0

def ping_checker():
    while True:
        for ip, _ in REMOTE_PC_LIST:
            online_status[ip] = ping(ip)
        time.sleep(5)

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
    global img_sent, pixel_sent, avg20, avg30, avg40, avg50
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
            
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-4]
        overlay = frame.copy()
        cv2.rectangle(overlay, (5, 3), (225, 25), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)
        cv2.putText(frame, ts, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        
        resized = cv2.resize(frame, (0, 0), fx=1, fy=1)
        success, jpeg = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        
        if success:
            if len(jpeg) >= 60000:
                success, jpeg = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
            
            if success and len(jpeg) < 60000:
                for ip, _ in REMOTE_PC_LIST:
                    if online_status[ip]:
                        sock_img.sendto(jpeg.tobytes(), (ip, IMAGE_PORT))
                        img_sent += 1
        time.sleep(interval)

# [修改] 具備熱插拔(斷線自動重連)功能的麥克風收音發送函數
def send_audio():
    global audio_sent
    CHUNK = 2048  # 約 0.128 秒的音訊片段 (16000Hz)
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000

    while True:  # 外層：無限重試連線迴圈
        p = pyaudio.PyAudio()
        stream = None
        try:
            # 嘗試開啟麥克風，如果沒插麥克風這裡會報錯並跳到 except
            stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
            print("🎙️ 麥克風收音啟動成功 / 已重新連線！")
            
            while True:  # 內層：成功連線後的讀取與發送迴圈
                # 當麥克風在運作途中被拔除時，read() 會拋出 OSError
                data = stream.read(CHUNK, exception_on_overflow=False)
                
                for ip, _ in REMOTE_PC_LIST:
                    if online_status[ip]:
                        sock_audio.sendto(data, (ip, AUDIO_PORT))
                        audio_sent += 1
                        
        except Exception as e:
            # 捕捉到沒有麥克風或途中被拔除的錯誤
            print(f"⚠️ 音訊設備未就緒或已拔除，2秒後重試... (原因: {e})")
            
        finally:
            # 【重要】發生錯誤時，必須安全釋放資源，才能在下一次迴圈抓到重插的設備
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except:
                    pass
            p.terminate() 
            
        # 避免無麥克風時狂轉吃滿 CPU，休息 2 秒再重試
        time.sleep(2)

def print_status():
    while True:
        os.system('cls' if platform.system().lower() == 'windows' else 'clear')
        print(f"  avg20 = {avg20}")
        print(f"  ADXL355: {adxl_sent} | 圖像: {img_sent} | 音訊: {audio_sent}")
        for ip, _ in REMOTE_PC_LIST:
            status = "Online" if online_status[ip] else "Offline"
            print(f"  {ip} : {status}")
        time.sleep(10)

if __name__ == "__main__":
    time.sleep(10)
    setup_adxl355()
    threading.Thread(target=ping_checker, daemon=True).start()
    threading.Thread(target=send_adxl355, daemon=True).start()
    threading.Thread(target=send_camera, daemon=True).start()
    threading.Thread(target=send_audio, daemon=True).start() # [新增] 啟動音訊執行緒
    threading.Thread(target=print_status, daemon=True).start()
    
    print("🟢 系統啟動中... Ctrl+C 可中斷")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        sock_adxl.close()
        sock_img.close()
        sock_pixel.close()
        sock_audio.close()
        print("🔴 手動中斷")

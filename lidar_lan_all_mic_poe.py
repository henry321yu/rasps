import cv2
import time
import socket
import os
import platform
import threading
import smbus2
from datetime import datetime
import subprocess # 新增 subprocess 來呼叫 FFmpeg

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
AUDIO_PORT = 2890  
CONTROL_PORT = 2895 
sock_adxl = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_img = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_pixel = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
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

# [新增] 全域變數，永遠存放最新的一張 RTSP 畫面
latest_rtsp_frame = None

# [新增] 獨立的 RTSP 讀取執行緒 (負責把緩衝區清空，模仿 USB WebCam 的行為)
def rtsp_reader_thread():
    global latest_rtsp_frame
    
    # 強制使用 TCP 傳輸，徹底解決 UDP 掉包導致的灰畫面/破圖
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    
    # 建議把 sub (子碼流) 放前面，降低 Pi 4B 的 H.264 解碼壓力
    rtsp_urls = [
        "rtsp://192.168.137.77:554/ch01_sub.264",
        "rtsp://192.168.137.77:554/ch01.264"
    ]
    url_index = 0
    
    while True:
        cap = cv2.VideoCapture(rtsp_urls[url_index], cv2.CAP_FFMPEG)
        # 嘗試將 OpenCV 緩衝區設為最小 (對部分版本有效)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        if not cap.isOpened():
            url_index = 1 - url_index
            time.sleep(2)
            continue
            
        while True:
            # 這裡沒有任何 sleep，全速狂讀，確保拿到的 frame 永遠是即時的
            ret, frame = cap.read() 
            if not ret:
                break # 讀取失敗(斷線)，跳出內迴圈重新連線
                
            latest_rtsp_frame = frame
            
        cap.release()
        url_index = 1 - url_index
        time.sleep(2)

# [修改] 影像處理與發送執行緒 (只負責拿最新畫面處理並發送)
def send_camera():
    global img_sent, latest_rtsp_frame, image_quality
    interval = 0.05
    
    while True:
        # 如果還沒讀到畫面，稍等一下
        if latest_rtsp_frame is None:
            time.sleep(0.1)
            continue
            
        # 複製最新的一張畫面來處理，完全不卡 RTSP 讀取的速度
        frame = latest_rtsp_frame.copy()
        
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        overlay = frame.copy()
        # cv2.rectangle(overlay, (5, 3), (234, 25), (0, 0, 0), -1) 
        # cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)
        # cv2.putText(frame, ts, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        cv2.rectangle(frame, (5, 3), (234, 25), (0, 0, 0), -1)
        cv2.putText(frame, ts, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        
        resized = cv2.resize(frame, (960, 540))
        
        success, jpeg = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), image_quality])
        
        if success:
            if len(jpeg) >= 60000:
                low_quality = max(0, image_quality - 20)
                success, jpeg = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), low_quality]) 
            
            if success and len(jpeg) < 60000:
                for ip, _ in REMOTE_PC_LIST:
                    if online_status[ip]:
                        sock_img.sendto(jpeg.tobytes(), (ip, IMAGE_PORT))
                        img_sent += 1
                        
        # 恢復你原本的設計：控制發送頻率，不用怕影響讀取端
        time.sleep(interval)

# [已修改] 從 RTSP 串流擷取音訊並發送
def send_audio():
    global audio_sent
    CHUNK = 2048  
    
    # 這裡填入有包含聲音的 RTSP 網址
    rtsp_url = "rtsp://192.168.137.77:554/ch01.264" 

    # FFmpeg 指令：提取 RTSP 音訊，並轉換為 16kHz, 單聲道, 16-bit PCM
    command = [
        'ffmpeg',
        '-rtsp_transport', 'tcp',  # 強制使用 TCP 傳輸，避免 UDP 掉包導致音訊碎裂/爆音
        '-i', rtsp_url,
        '-vn',                     # 略過影像解碼 (Video None)，大幅節省 Pi 4B CPU 效能
        '-acodec', 'pcm_s16le',    # 轉為 16-bit PCM (Little Endian)
        '-ar', '16000',            # 取樣率 16000 Hz (對齊你前端的 AudioContext)
        '-ac', '1',                # 單聲道
        '-f', 's16le',             # 輸出為原始 raw data
        '-'                        # 輸出至 stdout 讓 Python 讀取
    ]

    while True:
        process = None
        try:
            # 啟動 FFmpeg 子程序 (隱藏標準錯誤輸出，保持終端機乾淨)
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            
            while True:
                # 每次讀取 CHUNK 大小的音訊資料
                data = process.stdout.read(CHUNK)
                
                if not data:
                    break # 讀取不到資料代表串流中斷
                
                for ip, _ in REMOTE_PC_LIST:
                    if online_status[ip]:
                        sock_audio.sendto(data, (ip, AUDIO_PORT))
                        audio_sent += 1
                        
        except Exception as e:
            pass
        finally:
            if process:
                process.kill()
                process.wait() # 確保程序被完整釋放
        
        time.sleep(2) # 斷線後等待 2 秒重試

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
    
    # [新增] 啟動背景 RTSP 讀取執行緒
    threading.Thread(target=rtsp_reader_thread, daemon=True).start()

    threading.Thread(target=send_camera, daemon=True).start()
    threading.Thread(target=send_audio, daemon=True).start() 
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
        sock_control.close()
        print("🔴 手動中斷")
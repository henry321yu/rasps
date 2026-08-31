import cv2
import time
import socket
import os
import platform
import threading
import smbus2
from datetime import datetime
import subprocess

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
IMAGE_PORT = 2885 # 改為 TCP
AUDIO_PORT = 2890  
CONTROL_PORT = 2895 

sock_adxl = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_audio = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  
sock_control = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
sock_control.bind(("0.0.0.0", CONTROL_PORT))

# ========= 狀態變數 =========
online_status = {ip: True for ip, _ in REMOTE_PC_LIST}
avg20 = avg30 = avg40 = avg50 = 100
adxl_sent = img_sent = audio_sent = 0
image_quality = 70 
image_rate_ms = 500

def ping(ip):
    param = "-n" if platform.system().lower() == "windows" else "-c"
    return os.system(f"ping {param} 1 {ip} > /dev/null 2>&1") == 0

def ping_checker():
    while True:
        for ip, _ in REMOTE_PC_LIST:
            online_status[ip] = ping(ip)
        time.sleep(5)

def control_receiver():
    global image_quality, image_rate_ms
    while True:
        try:
            data, addr = sock_control.recvfrom(1024)
            msg = data.decode("utf-8")
            if msg.startswith("QUALITY:"):
                new_q = int(msg.split(":")[1])
                image_quality = new_q
            elif msg.startswith("RATE:"):      # [新增] 接收 Rate 控制指令
                new_r = int(msg.split(":")[1])
                image_rate_ms = max(10, new_r) # 防止數值過小導致除以零或系統當機
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

# ==========================================
# [新增] 背景全速讀取攝影機，永遠只保留「最新」的一張畫面
# ==========================================
latest_rtsp_frame = None
rtsp_ret = False
rtsp_lock = threading.Lock()

def camera_reader_thread():
    global latest_rtsp_frame, rtsp_ret
    cap = cv2.VideoCapture(RTSP_URL)
    # 嘗試強制減少 OpenCV 內部緩衝區 (視底層驅動而定)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) 
    
    while True:
        if not cap.isOpened():
            time.sleep(1)
            cap = cv2.VideoCapture(RTSP_URL)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            continue
            
        # 全速讀取，不加 sleep，避免畫面堆積在緩衝區造成延遲
        ret, frame = cap.read()
        
        with rtsp_lock:
            rtsp_ret = ret
            if ret:
                latest_rtsp_frame = frame
            else:
                latest_rtsp_frame = None
                
        if not ret:
            print("⚠️ RTSP 斷線，嘗試重連...")
            cap.release()
            time.sleep(1)


# ==========================================
# 依照設定的 Rate 抽取最新畫面，交給 FFmpeg
# ==========================================
def send_camera():
    global img_sent, image_quality, image_rate_ms, latest_rtsp_frame, rtsp_ret
    
    # 啟動背景抓圖執行緒
    threading.Thread(target=camera_reader_thread, daemon=True).start()
    
    process = None
    tcp_socks = {}
    current_quality = image_quality
    current_rate = image_rate_ms

    def broadcast_h264(proc):
        global img_sent
        while True:
            try:
                data = proc.stdout.read(8192)
                if not data:
                    break
                for ip, _ in REMOTE_PC_LIST:
                    if online_status[ip]:
                        if ip not in tcp_socks:
                            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            # [新增] 關閉 Nagle 演算法，降低 TCP 網路延遲
                            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1) 
                            s.settimeout(2)
                            try:
                                s.connect((ip, IMAGE_PORT))
                                tcp_socks[ip] = s
                            except:
                                continue
                        try:
                            tcp_socks[ip].sendall(data)
                            img_sent += 1
                        except:
                            tcp_socks[ip].close()
                            del tcp_socks[ip]
            except:
                break

    while True:
        # 若網頁端調整「畫質」或「Rate(FPS)」，重啟 FFmpeg
        if current_quality != image_quality or current_rate != image_rate_ms:
            if process:
                process.kill()
                process = None
            current_quality = image_quality
            current_rate = image_rate_ms

        if process is None or process.poll() is not None:
            crf_val = str(int(40 - ((current_quality - 20) / 80) * 25))
            fps_int = max(1, int(1000 / current_rate))
            fps_val = str(fps_int)
            
            cmd = [
                'ffmpeg', '-y',
                '-f', 'rawvideo', '-vcodec', 'rawvideo', '-pix_fmt', 'bgr24',
                '-s', '1920x1080', '-r', fps_val,
                '-i', '-', 
                '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'zerolatency',
                '-g', fps_val, '-keyint_min', fps_val, # 強制 I-frame 解決載入灰畫面
                '-crf', crf_val, '-f', 'h264', '-'
            ]
            process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            threading.Thread(target=broadcast_h264, args=(process,), daemon=True).start()

        # [修改] 這裡不呼叫 cap.read()，而是直接從背景執行緒拿「最新的一張」
        with rtsp_lock:
            ret = rtsp_ret
            # 使用 copy() 避免影像在處理時被背景執行緒覆寫導致破圖
            frame = latest_rtsp_frame.copy() if (ret and latest_rtsp_frame is not None) else None

        if not ret or frame is None:
            time.sleep(0.1)
            continue
            
        frame = cv2.resize(frame, (1920, 1080))    
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        overlay = frame.copy()
        cv2.rectangle(overlay, (5, 3), (234, 25), (0, 0, 0), -1) 
        cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)
        cv2.putText(frame, ts, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        
        try:
            process.stdin.write(frame.tobytes())
            process.stdin.flush() # [新增] 強制推送資料到 FFmpeg，減少卡頓
        except:
            if process:
                process.kill()
                process = None
                
        # 依照網頁端設定的 Rate 休息 (例如 500ms = 一秒跑兩次迴圈送給 FFmpeg)
        time.sleep(current_rate / 1000.0)

def send_audio():
    global audio_sent
    CHUNK = 2048

    while True:
        process = None
        try:
            command = [
                'ffmpeg', '-i', RTSP_URL,
                '-f', 's16le', '-acodec', 'pcm_s16le',
                '-ac', '1', '-ar', '16000',
                '-vn', '-sn', '-loglevel', 'quiet', '-'
            ]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("🎙️ RTSP 音訊收音啟動成功！")
            
            while True:
                data = process.stdout.read(CHUNK)
                if not data:
                    break 
                for ip, _ in REMOTE_PC_LIST:
                    if online_status[ip]:
                        sock_audio.sendto(data, (ip, AUDIO_PORT))
                        audio_sent += 1
        except Exception as e:
            pass
        finally:
            if process:
                process.kill()
                process.wait()
        time.sleep(2)

def print_status():
    while True:
        os.system('cls' if platform.system().lower() == 'windows' else 'clear')
        print(f"  avg20 = {avg20}")
        print(f"  ADXL355: {adxl_sent} | 圖像(TCP): {img_sent} | 音訊: {audio_sent} | 當前畫質: {image_quality}")
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
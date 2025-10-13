#!/usr/bin/env python3
# pi_sender.py
# Raspberry Pi: capture from /dev/video0 -> encode JPEG -> send to receiver via TCP
# 要求: python3, opencv-python

import cv2
import socket
import struct
import time
from datetime import datetime

# 設定：接收端 ZeroTier IP 與 port
DEST_IP = "10.241.135.1"
DEST_PORT = 5200

# 攝影機設定
CAM_DEVICE = 0  # /dev/video0
WIDTH = 640
HEIGHT = 480
FPS = 20
JPEG_QUALITY = 80  # 0-100，數值越大品質越好但資料越大

def draw_timestamp(frame):
    """在畫面右下角畫上當前時間 (白字, 無黑底)"""
    # 取當前時間，格式到百分之一秒 (小數點後兩位)
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S.") + f"{int(now.microsecond/10000):02d}"

    # 文字屬性
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    color = (255, 255, 255)  # 白色
    thickness = 1

    # 計算文字大小，用來確定右下角位置
    (text_w, text_h), _ = cv2.getTextSize(timestamp, font, font_scale, thickness)
    x = frame.shape[1] - text_w - 10  # 右邊留 10px
    y = frame.shape[0] - 10           # 下邊留 10px

    # 畫文字    cv2.putText(frame, timestamp, (x, y), font, font_scale, color, thickness, cv2.LINE_AA)
    return frame

def main():
    # 打開攝影機
    cap = cv2.VideoCapture(CAM_DEVICE, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, FPS)

    if not cap.isOpened():
        print("無法開啟攝影機，檢查 /dev/video0 或權限")
        return

    while True:
        try:
            print(f"嘗試連線到 {DEST_IP}:{DEST_PORT} ...")
            sock = socket.create_connection((DEST_IP, DEST_PORT), timeout=10)
            print("已連線，開始傳影像...")
            with sock:
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        print("讀取影格失敗，重新嘗試捕捉...")
                        time.sleep(0.5)
                        continue

                    # 在右下角疊上時間戳
                    frame = draw_timestamp(frame)

                    # 將 BGR 影格壓成 JPEG bytes
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
                    result, jpg = cv2.imencode(".jpg", frame, encode_param)
                    if not result:
                        print("JPEG 編碼失敗，跳過此影格")
                        continue
                    data = jpg.tobytes()

                    # 傳送：先傳 4 bytes 長度（network byte order big-endian），再傳資料
                    length = struct.pack(">I", len(data))
                    sock.sendall(length)
                    sock.sendall(data)

                    # 控制傳送速率
                    time.sleep(1.0 / FPS)

        except (ConnectionRefusedError, socket.timeout) as e:
            print("連線失敗或逾時：", e)
            time.sleep(2)
        except BrokenPipeError:
            print("連線中斷（BrokenPipe），準備重連...")
            time.sleep(1)
        except Exception as ex:
            print("發生例外：", ex)
            time.sleep(2)

if __name__ == "__main__":
    main()

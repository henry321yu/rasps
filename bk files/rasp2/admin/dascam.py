#!/usr/bin/env python3
# pi_sender_multi_stable.py
# Long-run stable version (365 days design)

import cv2
import socket
import struct
import time
import threading
from datetime import datetime

# ========= 傳送目標 =========
TARGETS = [
    ('10.241.0.114', 5200),
    ('10.241.135.1', 5200),
    ('10.241.199.211', 5200),
    ('10.241.215.99', 5200),
]

# ========= 攝影機設定 =========
CAM_DEVICE = 0
WIDTH = 640
HEIGHT = 480
FPS = 10
JPEG_QUALITY = 50

# ========= 系統參數 =========
SOCKET_TIMEOUT = 5
CAMERA_REOPEN_INTERVAL = 5
FRAME_EXPIRE_SEC = 2

# ========= 全域共享 =========
lock = threading.Lock()
latest_jpeg = None
last_frame_time = 0


# ---------- Timestamp ----------
def draw_timestamp(frame):
    now = datetime.now()
    ts = now.strftime("%Y-%m-%d %H:%M:%S.") + f"{int(now.microsecond/10000):02d}"
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.6
    color = (255, 255, 255)
    thickness = 1
    (w, h), _ = cv2.getTextSize(ts, font, scale, thickness)
    x = frame.shape[1] - w - 10
    y = frame.shape[0] - 10
    cv2.putText(frame, ts, (x, y), font, scale, color, thickness, cv2.LINE_AA)
    return frame


# ---------- Camera Thread ----------
def camera_thread():
    global latest_jpeg, last_frame_time

    cap = None

    while True:
        try:
            if cap is None or not cap.isOpened():
                print("[CAM] 開啟攝影機...")
                cap = cv2.VideoCapture(CAM_DEVICE, cv2.CAP_V4L2)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
                cap.set(cv2.CAP_PROP_FPS, FPS)
                time.sleep(1)

            ret, frame = cap.read()
            if not ret:
                print("[CAM] 讀取失敗，重開攝影機")
                cap.release()
                cap = None
                time.sleep(CAMERA_REOPEN_INTERVAL)
                continue

            frame = draw_timestamp(frame)

            ok, jpg = cv2.imencode(
                ".jpg",
                frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
            )
            if not ok:
                print("[CAM] JPEG encode 失敗")
                continue

            with lock:
                latest_jpeg = jpg.tobytes()
                last_frame_time = time.time()

            time.sleep(1.0 / FPS)

        except Exception as e:
            print(f"[CAM] Exception: {e}")
            if cap:
                cap.release()
                cap = None
            time.sleep(CAMERA_REOPEN_INTERVAL)


# ---------- Sender Thread ----------
def sender_thread(ip, port):
    global latest_jpeg, last_frame_time

    while True:
        try:
            print(f"[{ip}] 連線中...")
            sock = socket.create_connection((ip, port), timeout=SOCKET_TIMEOUT)
            sock.settimeout(SOCKET_TIMEOUT)
            print(f"[{ip}] 已連線")

            with sock:
                while True:
                    with lock:
                        data = latest_jpeg
                        age = time.time() - last_frame_time

                    if data is None or age > FRAME_EXPIRE_SEC:
                        time.sleep(0.05)
                        continue

                    length = struct.pack(">I", len(data))
                    sock.sendall(length)
                    sock.sendall(data)

                    time.sleep(1.0 / FPS)

        except (socket.timeout, ConnectionRefusedError, BrokenPipeError) as e:
            print(f"[{ip}] 連線問題：{e}，重試中...")
            time.sleep(2)
        except Exception as e:
            print(f"[{ip}] 未知錯誤：{e}")
            time.sleep(2)


# ---------- Main ----------
def main():
    threading.Thread(target=camera_thread, daemon=True).start()

    for ip, port in TARGETS:
        threading.Thread(
            target=sender_thread,
            args=(ip, port),
            daemon=True
        ).start()

    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()

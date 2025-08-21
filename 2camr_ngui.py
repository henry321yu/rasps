import cv2
import time
from datetime import datetime

def get_filename(cam_id):
    # 回傳依時間命名的檔名，例如 "202508111607_cam1.avi"
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"/home/admin/Desktop/video/{now}_cam{cam_id}.avi"

def create_video_writer(filename, width, height, fps):
    # 使用 MJPG 編碼，寫入 AVI 檔案
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    return cv2.VideoWriter(filename, fourcc, fps, (width, height))

# 攝像頭設定
width, height, fps = 640, 480, 20

cap0 = cv2.VideoCapture(0)
cap0.set(cv2.CAP_PROP_FRAME_WIDTH, width)
cap0.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
cap0.set(cv2.CAP_PROP_FPS, fps)

cap2 = cv2.VideoCapture(2)
cap2.set(cv2.CAP_PROP_FRAME_WIDTH, width)
cap2.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
cap2.set(cv2.CAP_PROP_FPS, fps)

if not cap0.isOpened():
    print("無法打開攝像頭 /dev/video0")
    cap0.release()
    cap2.release()
    exit()

if not cap2.isOpened():
    print("無法打開攝像頭 /dev/video2")
    cap0.release()
    cap2.release()
    exit()

# 先定義檔名
filename0 = get_filename(1)
filename2 = get_filename(2)

# 建立錄影器
writer0 = create_video_writer(filename0, width, height, fps)
writer2 = create_video_writer(filename2, width, height, fps)

start_time = time.time()
interval = 5 * 60  # 5 分鐘切換一次檔案

print("成功開啟兩個攝像頭並開始錄影 (按 Ctrl+C 停止)")
print(f"目前檔案：\n{filename0}\n{filename2}")

try:
    while True:
        ret0, frame0 = cap0.read()
        ret2, frame2 = cap2.read()

        if not ret0:
            print("攝像頭 /dev/video0 無法讀取畫面")
            break
        if not ret2:
            print("攝像頭 /dev/video2 無法讀取畫面")
            break

        # 時間字串
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-4]

        # 在影像上畫時間
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        color = (255, 255, 255)
        thickness = 1

        (text_w, text_h), baseline = cv2.getTextSize(now_str, font, font_scale, thickness)
        org0 = (width - text_w - 10, height - 10)
        org2 = (width - text_w - 10, height - 10)

        cv2.putText(frame0, now_str, org0, font, font_scale, color, thickness, cv2.LINE_AA)
        cv2.putText(frame2, now_str, org2, font, font_scale, color, thickness, cv2.LINE_AA)

        # 寫入錄影檔
        writer0.write(frame0)
        writer2.write(frame2)

        # 判斷是否超過 interval，若是就換新檔案
        elapsed = time.time() - start_time
        if elapsed > interval:
            writer0.release()    
            writer2.release()
            
            # 先定義檔名
            filename0 = get_filename(1)
            filename2 = get_filename(2)

            # 建立錄影器
            writer0 = create_video_writer(filename0, width, height, fps)
            writer2 = create_video_writer(filename2, width, height, fps)

            start_time = time.time()
            print(f"切換新錄影檔案：\n{filename0}\n{filename2}")

except KeyboardInterrupt:
    print("收到 Ctrl+C，停止錄影")

# 清理
cap0.release()
cap2.release()
writer0.release()
writer2.release()

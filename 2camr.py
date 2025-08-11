import cv2
import time
from datetime import datetime

def get_filename(cam_id):
    # 回傳依時間命名的檔名，例如 "202508111607_cam1.avi"
    now = datetime.now().strftime("%Y%m%d%H%M")
    return f"/home/admin/Desktop/video/{now}_cam{cam_id}.avi"

def create_video_writer(filename, width, height, fps=15):
    # 使用 MJPG 編碼，寫入 AVI 檔案
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    return cv2.VideoWriter(filename, fourcc, fps, (width, height))

# 攝像頭設定
width, height, fps = 640, 480, 15

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
    cv2.destroyAllWindows()
    exit()

if not cap2.isOpened():
    print("無法打開攝像頭 /dev/video2")
    cap0.release()
    cap2.release()
    cv2.destroyAllWindows()
    exit()

# 初始化錄影器與計時器
writer0 = create_video_writer(get_filename(1), width, height, fps)
writer2 = create_video_writer(get_filename(2), width, height, fps)
start_time = time.time()
interval = 2 * 60  # 5分鐘切換一次檔案

print("成功開啟兩個攝像頭並開始錄影，按 q 離開")

while True:
    ret0, frame0 = cap0.read()
    ret2, frame2 = cap2.read()

    if not ret0:
        print("攝像頭 /dev/video0 無法讀取畫面")
        break
    if not ret2:
        print("攝像頭 /dev/video2 無法讀取畫面")
        break

    # 顯示畫面
    cv2.imshow('Camera 0 (/dev/video0)', frame0)
    cv2.imshow('Camera 2 (/dev/video2)', frame2)

    # 寫入錄影檔
    writer0.write(frame0)
    writer2.write(frame2)

    # 判斷是否超過5分鐘，若是就換新檔案
    elapsed = time.time() - start_time
    if elapsed > interval:
        writer0.release()
        writer2.release()
        writer0 = create_video_writer(get_filename(1), width, height, fps)
        writer2 = create_video_writer(get_filename(2), width, height, fps)
        start_time = time.time()
        print("切換新錄影檔案")

    # 按 q 鍵退出
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 清理
cap0.release()
cap2.release()
writer0.release()
writer2.release()
cv2.destroyAllWindows()

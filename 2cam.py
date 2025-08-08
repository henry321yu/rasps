import cv2

# 開啟 /dev/video0
cap0 = cv2.VideoCapture(0)
cap0.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap0.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap0.set(cv2.CAP_PROP_FPS, 15)

# 開啟 /dev/video2
cap2 = cv2.VideoCapture(2)
cap2.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap2.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap2.set(cv2.CAP_PROP_FPS, 15)

# 驗證是否成功開啟攝像頭
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

print("成功開啟兩個攝像頭，按 q 離開")

while True:
    ret0, frame0 = cap0.read()
    ret2, frame2 = cap2.read()

    if not ret0:
        print("攝像頭 /dev/video0 無法讀取畫面")
        break
    if not ret2:
        print("攝像頭 /dev/video2 無法讀取畫面")
        break

    # 顯示兩個畫面
    cv2.imshow('Camera 0 (/dev/video0)', frame0)
    cv2.imshow('Camera 2 (/dev/video2)', frame2)

    # 按下 q 鍵離開
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 清理資源
cap0.release()
cap2.release()
cv2.destroyAllWindows()

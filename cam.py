import cv2

cap = cv2.VideoCapture(0)  # /dev/video0

if not cap.isOpened():
    print("無法打開攝像頭")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("無法讀取畫面")
        break

    cv2.imshow('Webcam', frame)

    # 按 q 離開
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
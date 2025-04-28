import socket

# 接收設定
LOCAL_IP = "0.0.0.0"  # 綁所有IP（不限定來源IP）
LOCAL_PORT = 2370     # 必須跟送端一樣

# 建立UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((LOCAL_IP, LOCAL_PORT))

print(f"開始接收來自PORT {LOCAL_PORT} 的資料...")

# 不停接收
while True:
    try:
        data, addr = sock.recvfrom(1024)  # 最多收1024 bytes
        message = data.decode('utf-8')

        # 分割資料
        parts = message.split(',')
        if len(parts) == 5:
            ID = parts[0]
            ax = float(parts[1])
            ay = float(parts[2])
            az = float(parts[3])
            tem = float(parts[4])
            
            # 印出變數
            print(f"{ID},{ax},{ay},{az},{tem}")

    except Exception as e:
        print(f"接收錯誤: {e}")

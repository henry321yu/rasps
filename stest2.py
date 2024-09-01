import socket

# 設定伺服器的 IP 和端口
HOST = "0.0.0.0"  # 本機 IP 地址
PORT = 5566        # 任意非特權端口


t0 = time.time()
# 創建一個 TCP/IP socket
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))  # 綁定 IP 和端口
    s.listen()            # 開始監聽傳入連接
    print(f"Server is listening on {HOST}:{PORT}...")

    conn, addr = s.accept()  # 接受一個新的連接
    with conn:
        print(f"Connected by {addr}")
        while True:
            t=time.time()-t0
            msg=str(round(t, 2))
            conn.sendall(msg)  # 回傳接收到的數據
            time.sleep(1)
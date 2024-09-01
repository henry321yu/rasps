import socket

HOST = ''  # 監聽所有可用的網絡接口
PORT = 5566  # 設置伺服器端口

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server listening on port {PORT}...")
        conn, addr = s.accept()
        with conn:
            print(f"Connected by {addr}")
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                print(f"Received data: {data.decode('utf-8')}")
                conn.sendall(data)  # Echo received data back to the client

if __name__ == "__main__":
    start_server()


# telnet mypc-heyri.zapto.org 5566
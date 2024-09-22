import os
import socket
from datetime import datetime

# 設定儲存檔案的資料夾路徑
# 替換為你想儲存檔案的資料夾路徑
# save_folder = r'C:\Users\fly\GB_Sar_and_GPS\log'
save_folder = r'C:\Users\弘銘\Desktop\WFH\git\log'

# 設定伺服器的 HOST 和 PORT
HOST = '0.0.0.0'  # 允許接收來自所有IP的連線
PORT = 5566  # 替換為伺服器的Port

# 建立伺服器來接收資料
def receive_file_from_network():

    data = ''
    try:
        # 如果存放檔案的資料夾不存在，則建立它
        if not os.path.exists(save_folder):
            os.makedirs(save_folder)

        # 建立伺服器 socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen(1)   # 伺服器允許最多 1 個連線請求
            print(f'Server listening on {HOST}:{PORT}')

            # 接受來自客戶端的連線
            conn, addr = s.accept()
            with conn:
                print(f'Connection established from {addr}')
                current_file = None
                file_name = None
                while True:
                    # 接收資料
                    data = conn.recv(1024).decode('utf-8')

                    # 如果沒有資料，則退出
                    if not data:
                        break

                    # 如果收到 FILENAME，則開始接收新檔案
                    if data.startswith("FILENAME:"):
                        # 關閉前一個檔案（如果有）
                        if current_file:
                            current_file.close()

                        # 提取檔案名稱並開啟新檔案來寫入
                 #       file_name = data.split("FILENAME:")[1]

                        current_time = datetime.now()
                        # 格式化日期和時間
                        file_name = "logger_"+current_time.strftime("%Y%m%d_%H%M%S")+".txt"


                        file_path = os.path.join(save_folder, file_name)
                        current_file = open(file_path, 'w', encoding='utf-8')
                        print(f"Receiving file: {file_name}")

                    # 如果收到 END_OF_FILE，則關閉檔案並等待下一個檔案
                    elif data == 'END_OF_FILE':
                        if current_file:
                            current_file.close()
                            print(f"Finished receiving file: {file_name}")
                            current_file = None

                    # 其他資料被視為檔案內容並寫入到當前的檔案
                    else:
                        if current_file:
                            current_file.write(data)
                            print(f"Received data for file {file_name}: {data.strip()}") # 刪了就有問題!! 見鬼了!!

    except Exception as e:
        print(f"Error occurred: {e}")


# 呼叫函數來進行檔案接收
FFF = 1
while FFF > 0:
    receive_file_from_network()
    print(FFF)
    FFF = FFF + 1

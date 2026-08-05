import os
import time
import socket
import threading
import configparser
import subprocess
import platform
from datetime import datetime
import psutil

BASE_DIR = os.getcwd()
CONFIG_FILE = os.path.join(BASE_DIR, "config.ini")
def get_port():
    config = configparser.ConfigParser()
    
    # 如果設定檔存在就讀取
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE, encoding="utf-8")

    # 若無 SETTINGS 區塊則新增
    if not config.has_section("SETTINGS"):
        config.add_section("SETTINGS")

    # 嘗試取得 port 並轉為 int
    if config.has_option("SETTINGS", "port"):
        try:
            port = int(config.get("SETTINGS", "port"))
            return port
        except ValueError:
            print("port 格式錯誤，使用預設值")

    # 預設值
    port = 5100
    config.set("SETTINGS", "port", str(port))
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        config.write(f)
    return port

def get_sync_folder():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    
    if not config.has_section("SETTINGS"):
        config.add_section("SETTINGS")
    
    if config.has_option("SETTINGS", "sync_folder"):
        folder_name = config.get("SETTINGS", "sync_folder").strip()
        if folder_name:
            return os.path.join(BASE_DIR, folder_name)
    
    # 預設為 sync_data
    folder_name = "sync_data"
    full_path = os.path.join(BASE_DIR, folder_name)
    os.makedirs(full_path, exist_ok=True)
    
    config.set("SETTINGS", "sync_folder", folder_name)
    with open(CONFIG_FILE, "w") as f:
        config.write(f)
    
    return full_path
FOLDER = get_sync_folder()
PORT = get_port()
SCAN_INTERVAL = 5
file_status = {}
sending = 0
receiving = 0
disnamelen = 15
extranamelen = 63
recive_mod = 0

def get_zerotier_ip():
    interfaces = psutil.net_if_addrs()
    for iface_name, iface_addrs in interfaces.items():
        if "zt" in iface_name:  # 介面通常開頭
            for addr in iface_addrs:
                if addr.family.name == 'AF_INET':  # IPv4
                    return iface_name, addr.address
    return None, None

def is_ip_reachable(ip):
    count_flag = "-n" if platform.system().lower() == "windows" else "-c"
    try:
        result = subprocess.run(
            ["ping", count_flag, "1", ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    except Exception:
        return False

def get_peer_ip():
    global recive_mod
    config = configparser.ConfigParser()

    iface, ip = get_zerotier_ip()
    # iface, ip = get_radmin_ip()
    if ip:
        print(f"虛擬LAN介面：{iface}\n本機虛擬LAN IP位址：{ip}")
    else:
        print("未偵測到 ZeroTier 虛擬LAN介面")
        # print("未偵測到 Radmin 虛擬LAN介面")

    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        if "SETTINGS" in config and "receiver_ip" in config["SETTINGS"]:
            ip = config["SETTINGS"]["receiver_ip"].strip()
            if is_ip_reachable(ip):
                print(f"[SETTINGS] 使用儲存的 IP：{ip} 連線成功")
                return ip
            else:
                print(f"[CONNECTION ERROR] 無法連線到儲存的 IP：{ip}，請重新輸入。")

    timeoutT = 5
    print(f"[CONNECTING] 請輸入接收方的IP(輸入空白或等待{timeoutT}秒進入接收模式)")
    while True:
        ip_input = [None]

        def timed_input():
            ip_input[0] = input("IP：").strip()

        t = threading.Thread(target=timed_input)
        t.daemon = True
        t.start()
        t.join(timeoutT)

        ip = ip_input[0] or ""

        if not ip:
            print("")
            print("[RECEIVE MODE] 接收模式 ...")
            recive_mod = 1
            return None  # 代表接收模式
        if is_ip_reachable(ip):
            print(f"[SYNC MODE] IP {ip} 連線成功，開始同步 ...")
            
            if not config.has_section("SETTINGS"):
                config.add_section("SETTINGS")
                
            config.set("SETTINGS", "receiver_ip", ip)
            
            with open(CONFIG_FILE, "w") as f:
                config.write(f)
            return ip
        else:
            timeoutT = 30
            print(f"[CONNECTION ERROR] 無法連線到 {ip}，請確認IP，輸入空白或等待{timeoutT}秒後自動進入接收模式。")

PEER_IP = get_peer_ip()

def send_file(file_path):
    global sending , receiving
    filename = os.path.basename(file_path)
    filesize = os.path.getsize(file_path)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((PEER_IP, PORT))
            s.send(len(filename.encode()).to_bytes(4, 'big'))
            s.send(filename.encode())
            s.send(filesize.to_bytes(8, 'big'))

            # 等待對方是否要跳過此檔案
            sending = 1 
            s.settimeout(10)  # 最多等待 10 秒回應
            try:
                response = s.recv(4).decode()
                if response == "SKIP":
                    print('\r' + ' ' * (disnamelen + extranamelen) + '\r', end='')
                    print(f"\r[SENDER][SKIP EXISTING] {filename}                                                ", end='', flush=True)
                    sending = 0
                    return True
            except socket.timeout:
                print('\r' + ' ' * (disnamelen + extranamelen) + '\r', end='')
                print(f"[SEND ERROR][{datetime.now().strftime('%H:%M:%S')}] {filename} - 等待對方回應超時 (10秒)")
                sending = 0
                return False
            finally:
                s.settimeout(None)  # 重設 timeout

            with open(file_path, 'rb') as f:
                sent = 0
                start_time = time.time()

                while chunk := f.read(4096):
                    s.sendall(chunk)
                    sent += len(chunk)
                    elapsed = time.time() - start_time                    
                    megabyte = 1024 * 1000
                    speed = sent / megabyte / elapsed if elapsed > 0 else 0
                    print_name = (filename[:disnamelen - 3] + '...') if len(filename) > disnamelen else filename            
                    eta = (filesize - sent)/ megabyte / speed if speed > 0 else 0
                    eta_str = time.strftime('%M:%S', time.gmtime(eta))
                    print(f"\r[SENDING]{print_name}:{filesize / megabyte:.2f} MB/{sent / megabyte:.2f} MB({speed:.2f} MB/S,{eta_str})", end='', flush=True)

                # 清除 SEND START 和 傳送進度輸出行
                print('\r' + ' ' * (disnamelen + extranamelen) + '\r', end='')
        sending = 0
        print(f"[SEND DONE][{datetime.now().strftime('%H:%M:%S')}] {filename} ({filesize / megabyte:.2f} MB)")
        return True
    except Exception as e:       
        sending = 0 
        print('\r' + ' ' * (disnamelen + extranamelen) + '\r', end='')
        print(f"[SEND ERROR][{datetime.now().strftime('%H:%M:%S')}] {filename} - {e}")
        return False 

def scan_and_sync_datasize_once():
    global sending
    for fname in os.listdir(FOLDER):
        full_path = os.path.join(FOLDER, fname)
        if os.path.isfile(full_path) and not fname.endswith(".tmp"):
            fsize = os.path.getsize(full_path)
            success = send_file(full_path)
            if success:
                continue
            else:
                print(f"[RETRY] 檔案 {fname} 同步失敗，將在下次掃描時再次嘗試")
    print('\r' + ' ' * (disnamelen + extranamelen) + '\r', end='')
    print(f"\r[SYNCED][{datetime.now().strftime('%H:%M:%S')}] ------- sync finished　----------", end='', flush=True)


def receiver():
    global sending , receiving
    os.makedirs(FOLDER, exist_ok=True)    
    # 啟動時清理 .tmp 檔
    for file in os.listdir(FOLDER):
        if file.endswith(".tmp"):
            tmp_path = os.path.join(FOLDER, file)
            try:
                os.remove(tmp_path)
                print(f"[CLEANUP] 開始前已刪除殘留暫存檔: {tmp_path}")
            except Exception as e:
                print(f"[CLEANUP ERROR] 無法刪除 {tmp_path}: {e}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', PORT))
        s.listen(5)
        print(f"[RECEIVER][{datetime.now().strftime('%H:%M:%S')}] Listening on port {PORT}...")

        while True:
            conn, addr = s.accept()
            with conn:
                while sending == 1:
                    time.sleep(1)
                try:
                    name_len = int.from_bytes(conn.recv(4), 'big')
                    filename = conn.recv(name_len).decode()
                    filesize = int.from_bytes(conn.recv(8), 'big')

                    final_file_path = os.path.join(FOLDER, filename)

                    # 檢查是否存在相同檔案（大小一致）
                    if os.path.exists(final_file_path) and os.path.getsize(final_file_path) == filesize:
                        conn.send(b"SKIP")
                        continue
                    else:
                        conn.send(b"OKAY")

                    receiving = 1
                    tmp_file_path = final_file_path + ".tmp"
                    with open(tmp_file_path, 'wb') as f:
                        received = 0
                        start_time = time.time()
                        while received < filesize:
                            data = conn.recv(min(4096, filesize - received))
                            if not data:
                                break
                            f.write(data)
                            received += len(data)
                            elapsed = time.time() - start_time
                            megabyte = 1024 * 1000
                            speed = received / megabyte / elapsed if elapsed > 0 else 0
                            print_name = (filename[:disnamelen-3] + '...') if len(filename) > disnamelen else filename
                            eta = (filesize - received)/ megabyte / speed if speed > 0 else 0
                            eta_str = time.strftime('%M:%S', time.gmtime(eta))
                            print(f"\r[RECEIVING][{addr[0]}]{print_name}:{filesize / megabyte:.2f} MB/{received / megabyte:.2f} MB({speed:.2f} MB/S,{eta_str})", end='', flush=True)

                    if os.path.exists(final_file_path):
                        os.remove(final_file_path)  # 刪除已存在的同名檔案
                    os.rename(tmp_file_path, final_file_path)
                    print('\r' + ' ' * (disnamelen + extranamelen) + '\r', end='')   # 清除行
                    print(f"[RECEIVE DONE][{datetime.now().strftime('%H:%M:%S')}][From:{addr[0]}]{filename} ({filesize / megabyte:.2f} MB)")
                    receiving = 0
                except Exception as e:
                    receiving = 0
                    print('\r' + ' ' * (disnamelen + extranamelen) + '\r', end='')   # 清除行
                    print(f"[RECEIVE ERROR][{datetime.now().strftime('%H:%M:%S')}] - {e}")
                    if tmp_file_path and os.path.exists(tmp_file_path):
                        try:
                            os.remove(tmp_file_path)
                            print(f"[CLEANUP] 已刪除不完整檔案 {tmp_file_path}")
                        except Exception as cleanup_error:
                            print(f"[CLEANUP ERROR] 刪除失敗: {cleanup_error}")

def main_loop():
    global sending, receiving
    print(f"[INFO][{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 開始自動同步模式")

    # 啟動接收器 socket server（持續執行，非阻塞）
    threading.Thread(target=receiver, daemon=True).start()

    while True:
        if recive_mod == 1:
            # 純接收模式，不進入同步
            time.sleep(1)
            continue

        # 若目前非傳送/接收中 → 執行同步掃描
        if sending == 0 and receiving == 0:
            scan_and_sync_datasize_once()
        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    try:
        print(f"[INFO]目標資料夾: {FOLDER}")
        os.makedirs(FOLDER, exist_ok=True)
        main_loop()
    except KeyboardInterrupt:
        print("\n[EXIT] 使用者中斷，程式結束")
    except Exception as e:
        print(f"[FATAL ERROR] 未預期錯誤導致程式終止：{e}")

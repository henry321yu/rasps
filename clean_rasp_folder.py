import paramiko
import time
import threading
import os
import datetime

# # 樹莓派登入資訊
# hostname = "192.168.255.1"
# username = "pi"
# password = "p@ssw0rd"  # 如果有設定密碼

# 要清空的資料夾
# remote_dir = "/home/pi/Desktop/vAlert/rec"
# remote_dir = "/home/pi/Desktop/test"

# LOG_DIR = r"C:\Users\MyUser\Desktop\auto_mic"
# LOG_DIR = r"C:\Users\b5566\Desktop\FTP\auto_mic"
# LOG_DIR = r"log"

# 樹莓派登入資訊
hostname = "10.241.136.93"
username = "admin"
password = "123"  # 如果有設定密碼

# # 要清空的資料夾
remote_dir = "/home/admin/Desktop/stepper"



LOG_DIR = r"C:\Users\sgrc - 325\Desktop\git\Codex\rasp\stepper"

# ------------------ Log 設定 ------------------
log_lock = threading.Lock()
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(
    LOG_DIR,
    f"clean_seis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
)

def log(msg, level="LOG", end="\n"):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    with log_lock:
        print(line, end=end, flush=True)
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            print(f"!! Log Write Error: {e}")

# ------------------ SSH 函數 ------------------
def run_ssh_command(ssh, command):
    stdin, stdout, stderr = ssh.exec_command(command)
    err = stderr.read().decode()
    out = stdout.read().decode()
    if err:
        log(f"SSH Error: {err}", level="ERROR")
    return out.strip()

def get_disk_usage(ssh):
    output = run_ssh_command(ssh, "df -h / | tail -1 | awk '{print $5}'")
    return output

def get_file_count(ssh, path):
    output = run_ssh_command(ssh, f"ls -1 {path} 2>/dev/null | wc -l")
    return int(output) if output.isdigit() else 0

def clear_folder(ssh, path):
    file_count = get_file_count(ssh, path)
    log(f"Cleaning {path}")
    if file_count == 0:
        log("Folder is empty")
        return 0

    files = run_ssh_command(ssh, f"ls -1 {path}").splitlines()
    deleted_count = 0
    for f in files:
        log(f"Deleting {f} ...")
        run_ssh_command(ssh, f"rm -rf '{path}/{f}'")
        deleted_count += 1
        time.sleep(0.1)  # 模擬進度
    return deleted_count

# ------------------ 主程式 ------------------
try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, username=username, password=password)
    log("Connection initialized")

    disk_before = get_disk_usage(ssh)
    file_count_before = get_file_count(ssh, remote_dir)
    log(f"Available disk space : {disk_before}")
    log(f"{remote_dir} Total {file_count_before} files")

    deleted_count = clear_folder(ssh, remote_dir)
    log(f"{remote_dir} Total {deleted_count} files deleted")

    disk_after = get_disk_usage(ssh)
    log(f"Available disk space : {disk_after}")

except Exception as e:
    log(f"Error : {e}", level="ERROR")
finally:
    try:
        ssh.close()
        log("SSH connection closed")
    except:
        pass
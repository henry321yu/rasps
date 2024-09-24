import time
import shutil
import os  # 確保引入 os 模組
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import configparser

# 確認 datapath.ini 是否存在，若不存在則生成
if not os.path.exists('copypath.ini'):
    print("copypath.ini 不存在，正在創建...")
    config = configparser.ConfigParser()
    config['Path1'] = {'from_folder_path': '請輸入來源資料夾路徑'}
    config['Path2'] = {'to_folder_path': '請輸入輸出資料夾路徑'}

    with open('copypath.ini', 'w') as configfile:
        config.write(configfile)
    print("copypath.ini 已生成，請開啟並設置資料夾路徑。")
    input("press enter to exit...")
    exit()

# 讀取INI檔案
config = configparser.ConfigParser()

try:
    config.read('copypath.ini')
except:
    print("copypath.ini error....")
    input("press enter to exit...")
    exit()

# 確認資料夾路徑是否已設置
source_folder = config['Path1']['from_folder_path']
destination_folder = config['Path2']['to_folder_path']

if source_folder == '請輸入來源資料夾路徑':
    print("請先在 copypath.ini 中設置來源資料夾路徑。")
    input("press enter to exit...")
    exit()
if destination_folder == '請輸入輸出資料夾路徑':
    print("請先在 copypath.ini 中設置輸出資料夾路徑。")
    input("press enter to exit...")
    exit()

print(f"copy from : {source_folder}")
print(f"copy to : {destination_folder}")

# 複製舊檔案
try:
    for file_name in os.listdir(source_folder):
        source_path = os.path.join(source_folder, file_name)
        destination_path = os.path.join(destination_folder, file_name)
        if os.path.isfile(source_path):
            shutil.copy(source_path, destination_path)
            print(f'檔案 {file_name} 已被複製到 {destination_folder}')
except:
    print("error wrong path or files maybe...")
    input("press enter to exit...")
    exit()

class FileHandler(FileSystemEventHandler):
    def on_created(self, event):
        # 當有新檔案加入時觸發
        if not event.is_directory:
            file_name = os.path.basename(event.src_path)  # 使用 os.path.basename 獲取檔名
            destination_path = os.path.join(destination_folder, file_name)
            shutil.copy(event.src_path, destination_path)
            print(f'檔案 {file_name} 已被複製到 {destination_folder}')

# 設定觀察器
event_handler = FileHandler()
observer = Observer()
observer.schedule(event_handler, path=source_folder, recursive=False)
observer.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()

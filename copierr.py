import shutil
import os
import configparser

# 確認 copypath.ini 是否存在，若不存在則生成
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
    with open('copypath.ini', 'r', encoding='utf-8') as f:
        config.read_file(f)
except Exception as e:
    print(f"copypath.ini error: {e}")
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
print('\n')


if not os.path.exists(source_folder):            
    print(f'來源資料夾 {source_folder} 不存在')
    input("press enter to exit...")
    exit()

input(f"按下 enter 確認複製所有自 {source_folder} 確認到的新檔案到 {destination_folder}...")
print('\n')

# 複製來源資料夾的所有檔案到目標資料夾
def copy_files(source, destination):
    global fileN,folderN
    fileN=folderN=0
    for root, dirs, files in os.walk(source):
        relative_path = os.path.relpath(root, source)  # 相對路徑
        dest_dir = os.path.join(destination, relative_path)

        # 如果目標資料夾不存在，則建立該資料夾        
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
            folderN+=1
            print(f'創建資料夾 {dest_dir}')

        # 複製檔案
        for file_name in files:
            source_file = os.path.join(root, file_name)
            destination_file = os.path.join(dest_dir, file_name)

            # 如果檔案不存在或來源檔案更新，則進行複製
            if not os.path.exists(destination_file) or os.path.getmtime(source_file) > os.path.getmtime(destination_file):
                print(f'複製 {file_name} 到 {destination_file}')
                shutil.copy2(source_file, destination_file)
                fileN+=1

# 初始複製來源資料夾內容
try:
    copy_files(source_folder, destination_folder)
    print('\n')
    print(f"已複製任何來自 {source_folder} 確認到的新檔案到 {destination_folder}")
    print(f"共複製 : {folderN} 個資料夾 , {fileN} 個檔案")
except Exception as e:
    print(f"複製檔案時發生錯誤：{e}")
    
input("press enter to exit...")
exit()
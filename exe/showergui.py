import os
import configparser
import tkinter as tk
from tkinter import messagebox
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from pyproj import Transformer

# 確認 datapath.ini 是否存在，若不存在則生成
if not os.path.exists('datapath.ini'):
    print("datapath.ini 不存在，正在創建...")
    config = configparser.ConfigParser()
    config['Paths'] = {'folder_path': '請輸入資料夾路徑'}
    
    with open('datapath.ini', 'w') as configfile:
        config.write(configfile)
    print("datapath.ini 已生成，請開啟並設置資料夾路徑。")
    input("press enter to exit...")
    exit() 

# 讀取INI檔案
config = configparser.ConfigParser()

try:
    with open('datapath.ini', 'r', encoding='utf-8') as f:
        config.read_file(f)
except Exception as e:
    print(f"datapath.ini error: {e}")
    input("press enter to exit...")
    exit()

# 確認資料夾路徑是否已設置
folder_path = config['Paths']['folder_path']
if folder_path == '請輸入資料夾路徑':
    print("請先在 datapath.ini 中設置資料夾路徑。")
    input("press enter to exit...")
    exit()

# 初始化一個空的 DataFrame 來儲存所有的資料
all_data = pd.DataFrame()

# TWD97 (EPSG:3826) 投影系統
transformer = Transformer.from_crs("EPSG:4326", "EPSG:3826")

# 用來儲存顏色的字典
color_map = {}
color_index = 0  # 用來追蹤顏色的索引

# 生成 100 個顏色
colors = []
num = [3, 5, 7]  # 設定隨機顏色參數
for j in range(100):
    r = ((j + num[0]) % num[2]) / num[2]
    g = ((j + num[1]) % num[1]) / num[1]
    b = ((j + num[2]) % num[0]) / num[0]
    colors.append((r, g, b))

figuresize=[7,4]
plotsize=3

print("Reading all .txt files...")

try:    
    global fileN,fileDN,dateN,sampleN
    fileN=fileDN=dateN=sampleN=0
    # 遍歷資料夾中的所有.txt檔案
    for filename in os.listdir(folder_path):
        if filename.endswith(".txt"):
            file_path = os.path.join(folder_path, filename)
            fileN+=1
            print(f"loading : {file_path}")
            
            # 提取日期
            date_str = filename.split('_')[1]  # 取得日期部分
            date = datetime.strptime(date_str, '%Y%m%d').date()
            
            # 隨機生成顏色或使用特定顏色
            if date not in color_map:
                color_map[date] = colors[color_index % len(colors)]  # 隨機顏色
                color_index += 1
                dateN+=1

            # 初始化一個暫存列表來存儲數據
            temp_data = []
            
            # 打開檔案逐行讀取
            with open(file_path, 'r') as file:
                for line in file:
                    if 'END_OF_FILE' in line:
                        break
                    split_line = line.strip().split()
                    if len(split_line) == 9:
                        split_line.extend(['0', '0'])  # 增加 'volt' 和 'current' 欄位為 0
                    temp_data.append(split_line)      

            if temp_data and len(temp_data) > 3:  # 檢查至少有3行數據
                data = pd.DataFrame(temp_data)
                data.columns = ['UTC+8', 'ax', 'ay', 'az', 'lat', 'lon', 'alt', 'gps_mode', 'temperature', 'volt', 'current']
                data['UTC+8'] = pd.to_datetime(data['UTC+8'], format='%H:%M:%S.%f', errors='coerce')
                data = data.dropna(subset=['UTC+8'])
                for col in data.columns[1:]:
                    data[col] = pd.to_numeric(data[col], errors='coerce')     
                data = data.dropna()

                if len(data) > 0:
                    twd97_x, twd97_y = transformer.transform(data['lat'].values, data['lon'].values)
                    data['twd97_x'] = twd97_x
                    data['twd97_y'] = twd97_y
                    data['date'] = date
                    all_data = pd.concat([all_data, data])
                    fileDN+=1
                    for _ in range(len(data)):
                        sampleN+=1
            else:
                print(f"Error reading {file_path}")
                
except Exception as e:
    print(f"Error reading files: {e}")
    input("press enter to exit...")
    exit()

# 確保數據按時間順序排序
try:
    all_data.sort_values(by='UTC+8', inplace=True)
except Exception as e:
    print(f"Error sorting data: {e}")
    input("press enter to exit...")
    exit()

print("finish loading...")
print(f"{fileN} 個檔案 , 共讀取 {fileDN} 個檔案 , 共 {dateN} 日 , {sampleN} 筆資料")

all_data = all_data[all_data['current'] != 0]  # 刪除 current 為 0
all_data = all_data[all_data['volt'] != 0]  # 刪除 volt 為 0
gps_mode_4_data = all_data[all_data['gps_mode'] == 4] # gps_mode 為 4 的資料

def plot_voltage():
    print("plot voltage...")
    # 繪製 Voltage 圖表
    plt.figure(figsize=(figuresize[0], figuresize[1]), num='voltage')

    for date, color in color_map.items():
        date_data = all_data[all_data['date'] == date]
        plt.plot(date_data['UTC+8'], date_data['volt'], '.', label=str(date), color=color, markersize=plotsize)

    plt.ylim(10, 15)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xlabel('time(UTC+8)')
    plt.ylabel('voltage(V)')
    plt.title('voltage')
    plt.xticks(rotation=45)
    plt.legend(title='cate')
    plt.tight_layout()
    plt.show(block=False)

def plot_current():
    print("plot current...")
    # 繪製 current 圖表
    plt.figure(figsize=(figuresize[0], figuresize[1]), num='current')

    for date, color in color_map.items():
        date_data = all_data[all_data['date'] == date]
        plt.plot(date_data['UTC+8'], date_data['current'], '.', label=str(date), color=color, markersize=plotsize)

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xlabel('time(UTC+8)')
    plt.ylabel('current(A)')
    plt.title('current')
    plt.xticks(rotation=45)
    plt.legend(title='date')
    plt.tight_layout()
    plt.show(block=False)

def plot_temperature():
    print("plot temperature...")
    # 繪製 temperature 圖表
    plt.figure(figsize=(figuresize[0], figuresize[1]), num='temperature')

    for date, color in color_map.items():
        date_data = all_data[all_data['date'] == date]
        plt.plot(date_data['UTC+8'], date_data['temperature'], '.', label=str(date), color=color, markersize=plotsize)

    plt.ylim(10, 60)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xlabel('time (UTC+8)')
    plt.ylabel('temperature(C)')
    plt.title('temperature')
    plt.xticks(rotation=45)
    plt.legend(title='date')
    plt.tight_layout()
    plt.show(block=False)

def plot_gps_mode():
    print("plot gps mode...")
    # 繪製 gps_mode 圖表
    plt.figure(figsize=(figuresize[0], figuresize[1]), num='gps mode')

    for date, color in color_map.items():
        date_data = all_data[all_data['date'] == date]
        plt.plot(date_data['UTC+8'], date_data['gps_mode'], '.', label=str(date), color=color, markersize=plotsize)

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xlabel('time(UTC+8)')
    plt.ylabel('gps mode')
    plt.title('gps mode')
    plt.xticks(rotation=45)
    plt.legend(title='date')
    plt.tight_layout()
    plt.show(block=False)

def plot_TWD97_x():
    print("plot TWD97 x...")
    # 繪製 twd97_x vs UTC+8 (僅限 gps_mode 為 4 的數據)
    plt.figure(figsize=(figuresize[0], figuresize[1]), num='TWD97 x')

    for date, color in color_map.items():
        date_gps_data = gps_mode_4_data[gps_mode_4_data['date'] == date]
        plt.plot(date_gps_data['UTC+8'], date_gps_data['twd97_x'], '.', label=str(date), color=color, markersize=plotsize)

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xlabel('time(UTC+8)')
    plt.ylabel('TWD97 x(m)')
    plt.title('TWD97 x')
    plt.xticks(rotation=45)
    plt.legend(title='date')
    plt.tight_layout()
    plt.show(block=False)

def plot_TWD97_y():
    print("plot TWD97 y...")
    # 繪製 twd97_y vs UTC+8 (僅限 gps_mode 為 4 的數據)
    plt.figure(figsize=(figuresize[0], figuresize[1]), num='TWD97 y')

    for date, color in color_map.items():
        date_gps_data = gps_mode_4_data[gps_mode_4_data['date'] == date]
        plt.plot(date_gps_data['UTC+8'], date_gps_data['twd97_y'], '.', label=str(date), color=color, markersize=plotsize)

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xlabel('time(UTC+8)')
    plt.ylabel('TWD97 y(m)')
    plt.title('TWD97 y')
    plt.xticks(rotation=45)
    plt.legend(title='date')
    plt.tight_layout()
    plt.show(block=False)

def plot_altitude():
    print("plot altitude...")
    # 繪製 altitude 圖表
    plt.figure(figsize=(figuresize[0], figuresize[1]), num='altitude')

    for date, color in color_map.items():
        date_gps_data = gps_mode_4_data[gps_mode_4_data['date'] == date]
        plt.plot(date_gps_data['UTC+8'], date_gps_data['alt'], '.', label=str(date), color=color, markersize=plotsize)

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xlabel('time(UTC+8)')
    plt.ylabel('altitude(m)')
    plt.title('altitude')
    plt.xticks(rotation=45)
    plt.legend(title='date')
    plt.tight_layout()
    plt.show(block=False)

def plot_TWD97_xy():
    print("plot TWD97 xy...")
    # 繪製 twd97_y vs twd97_y 圖表
    plt.figure(figsize=(figuresize[0], figuresize[1]), num='TWD97 x  vs  TWD97 y')

    for date, color in color_map.items():
        date_gps_data = gps_mode_4_data[gps_mode_4_data['date'] == date]
        plt.plot(date_gps_data['twd97_x'], date_gps_data['twd97_y'], '.', label=str(date), color=color, markersize=plotsize)

    plt.xlabel('TWD97 x(m)')
    plt.ylabel('TWD97 y(m)')
    plt.title('TWD97 x  vs  TWD97 y')
    plt.legend(title='date')
    plt.tight_layout()
    plt.show(block=False)

def plot_accelerometer_x():
    print("plot accelerometer x...")
    # 繪製 accelerometer x 圖表
    plt.figure(figsize=(figuresize[0], figuresize[1]), num='accelerometer x')

    for date, color in color_map.items():
        date_data = all_data[all_data['date'] == date]
        plt.plot(date_data['UTC+8'], date_data['ax'], '-', label=str(date), color=color, markersize=plotsize)

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xlabel('time(UTC+8)')
    plt.ylabel('ax(G)')
    plt.title('accelerometer x')
    plt.xticks(rotation=45)
    plt.legend(title='date')
    plt.tight_layout()
    plt.show(block=False)

def plot_accelerometer_y():
    print("plot accelerometer y...")
    # 繪製 accelerometer y 圖表
    plt.figure(figsize=(figuresize[0], figuresize[1]), num='accelerometer y')

    for date, color in color_map.items():
        date_data = all_data[all_data['date'] == date]
        plt.plot(date_data['UTC+8'], date_data['ay'], '-', label=str(date), color=color, markersize=plotsize)

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xlabel('time(UTC+8)')
    plt.ylabel('ay(G)')
    plt.title('accelerometer y')
    plt.xticks(rotation=45)
    plt.legend(title='date')
    plt.tight_layout()
    plt.show(block=False)

def plot_accelerometer_z():
    print("plot accelerometer z...")
    # 繪製 accelerometer z 圖表
    plt.figure(figsize=(figuresize[0], figuresize[1]), num='accelerometer z')

    for date, color in color_map.items():
        date_data = all_data[all_data['date'] == date]
        plt.plot(date_data['UTC+8'], date_data['az'], '-', label=str(date), color=color, markersize=plotsize)

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xlabel('time(UTC+8)')
    plt.ylabel('az(G)')
    plt.title('accelerometer z')
    plt.xticks(rotation=45)
    plt.legend(title='date')
    plt.tight_layout()
    plt.show(block=False)

    
# 開啟所有 plot
def open_all_plots():
    print("opening all plots...")
    plot_voltage()
    plot_current()
    plot_temperature()
    plot_gps_mode()
    plot_altitude()
    plot_TWD97_x()
    plot_TWD97_y()
    plot_TWD97_xy()
    plot_accelerometer_x()
    plot_accelerometer_y()
    plot_accelerometer_z()

# 關閉所有 plot (可以是清除所有圖表，這裡是示範)
def close_all_plots():
    print("Closing all plots...")
    plt.close('all')

# 關閉程式
def close_program():
    root.quit()  # 結束 tkinter 事件循環
    root.destroy()  # 銷毀窗口，完全退出程式
    print("Program closed...")

# 建立 GUI 介面
def create_gui():
    print("create gui...")
    global root
    root = tk.Tk()
    root.title("Data Plotter")

    # 設定 GUI 大小
    root.geometry("240x720")
    
    # 設定按鈕樣式
    button_style = {
        'padx': 10,
        'pady': 1,
        'font': ("Arial", 8),
        'width': 15,  # 設定按鈕寬度
        'height': 1   # 設定按鈕高度
    }
    yy=4 #高度距
    
    
    # 顯示Label
    label_value = tk.Label(root, text="資料路徑 :", font=("Arial", 9)).pack(pady=0)
    label_value = tk.Label(root, text=f"{folder_path}", font=("Arial", 9), wraplength=230).pack(pady=1)
    tk.Label(root, text="").pack(pady=1)  # 空行
    
    label_value = tk.Label(root, text=f"內有 {fileN} 個檔案 , 共讀取 {fileDN} 個檔案", font=("Arial", 9)).pack(pady=1)
    label_value = tk.Label(root, text=f"共 {dateN} 日 , {sampleN} 筆資料", font=("Arial", 9)).pack(pady=1)
    tk.Label(root, text="").pack(pady=1)  # 空行
    
    tk.Label(root, text="請按下相應按鈕以繪製對應圖表", font=("Arial", 10)).pack(pady=yy)  
    tk.Button(root, text="voltage", command=plot_voltage, **button_style).pack(pady=yy)
    tk.Button(root, text="current", command=plot_current, **button_style).pack(pady=yy)
    tk.Button(root, text="temperature", command=plot_temperature, **button_style).pack(pady=yy)
    tk.Button(root, text="gps_mode", command=plot_gps_mode, **button_style).pack(pady=yy)
    tk.Button(root, text="altitude", command=plot_altitude, **button_style).pack(pady=yy)
    tk.Button(root, text="TWD97_x", command=plot_TWD97_x, **button_style).pack(pady=yy)
    tk.Button(root, text="TWD97_y", command=plot_TWD97_y, **button_style).pack(pady=yy)
    tk.Button(root, text="TWD97_xy", command=plot_TWD97_xy, **button_style).pack(pady=yy)
    tk.Button(root, text="accelerometer_x", command=plot_accelerometer_x, **button_style).pack(pady=yy)
    tk.Button(root, text="accelerometer_y", command=plot_accelerometer_y, **button_style).pack(pady=yy)
    tk.Button(root, text="accelerometer_z", command=plot_accelerometer_z, **button_style).pack(pady=yy)
    tk.Label(root, text="").pack(pady=yy)  # 空行
    
    # 開啟和關閉所有 plot 的按鈕
    tk.Button(root, text="開啟所有圖表", command=open_all_plots, bg="yellow", fg="black", **button_style).pack(pady=yy)
    tk.Button(root, text="關閉所有圖表", command=close_all_plots, bg="lightblue", fg="black", **button_style).pack(pady=yy)
    tk.Label(root, text="").pack(pady=yy)  # 空行
    
    tk.Button(root, text="EXIT", command=close_program, bg="grey", fg="black", **button_style).pack(pady=yy)


    root.mainloop()

# 啟動 GUI
create_gui()

exit() 
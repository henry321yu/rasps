import os
import configparser
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from pyproj import Transformer
import customtkinter as ctk
from tkinter import filedialog
from concurrent.futures import ThreadPoolExecutor  # 引入多線程

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

figuresize = [7, 4]
plotsize = 3

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


# GUI 打印訊息的函數
def log_message(msg):
    text_log.insert(ctk.END, msg + '\n')
    text_log.see(ctk.END)
    text_log.update_idletasks()  # 更新Tkinter界面


def load_file(file_path):
    global color_index
    date_str = os.path.basename(file_path).split('_')[1]  # 取得日期部分
    date = datetime.strptime(date_str, '%Y%m%d').date()

    # 隨機生成顏色或使用特定顏色
    if date not in color_map:
        color_map[date] = colors[color_index % len(colors)]  # 隨機顏色
        color_index += 1

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

    return date, temp_data

def process_data(file_data):
    date, temp_data = file_data

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
            return data
    return pd.DataFrame()  # 返回空的 DataFrame

def load_data(folder_path):
    global all_data
    all_data = pd.DataFrame()  # 清空之前的資料
    color_map.clear()
    file_paths = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".txt")]

    log_message(f"Reading all .txt files from {folder_path}...")

    # 使用 ThreadPoolExecutor 來加速讀取檔案
    with ThreadPoolExecutor() as executor:
        results = executor.map(load_file, file_paths)

    # 處理每個檔案的數據
    dataframes = []
    for result in results:
        data = process_data(result)
        if not data.empty:
            dataframes.append(data)

    # 合併所有讀取的 DataFrame
    if dataframes:
        all_data = pd.concat(dataframes, ignore_index=True)

    # 確保數據按時間順序排序
    all_data.sort_values(by='UTC+8', inplace=True)

    # 清除無效的資料
    all_data = all_data[all_data['current'] != 0]  # 刪除 current 為 0
    all_data = all_data[all_data['volt'] != 0]  # 刪除 volt 為 0
    gps_mode_4_data = all_data[all_data['gps_mode'] == 4]  # gps_mode 為 4 的資料

    log_message(f"Loaded {len(all_data)} records from {len(file_paths)} files.")

    return True


def select_folder():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        folder_path_label.configure(text=f"Folder: {folder_selected}")
        enable_buttons()
        if load_data(folder_selected):
            log_message("Data loaded successfully.")


def enable_buttons():
    # 啟用所有按鈕
    for button in buttons_list:
        button.configure(state="normal")

def create_gui():
    global root, folder_path_label, text_log, buttons_list

    # 設定主題
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("dark-blue")

    root = ctk.CTk()
    root.title("Data Plotter")
    root.geometry("540x720")

    # 按鈕樣式
    button_style = {
        'font': ("Arial", 12),
        'width': 120,
        'height': 30
    }
    xx = 20  # 寬度距
    yy = 5  # 高度距

    Folder_button = ctk.CTkButton(root, text="Select Folder", command=select_folder, font=("Arial", 12)).pack(padx=xx, pady=yy)

    # 顯示資料夾路徑的 Label
    folder_path_label = ctk.CTkLabel(root, text="No folder selected", font=("Arial", 12))
    folder_path_label.pack(pady=yy)

    # Log 紀錄框
    log_frame = ctk.CTkFrame(root)
    log_frame.pack(pady=yy, fill='both', expand=True)

    # 添加滾動條
    text_log = ctk.CTkTextbox(log_frame, width=400, height=100)
    text_log.pack(side='left', fill='both', expand=True)

    text_label = ctk.CTkLabel(root, text="").pack(padx=0, pady=0)

    # 繪圖按鈕區域
    button_frame = ctk.CTkFrame(root)
    button_frame.pack(expand=True)
    root.grid_columnconfigure(0, weight=1)
    
    # 添加 plot 按鈕，初始為 disabled
    buttons_list = []
    ctk.CTkLabel(button_frame, text="Select Plot：", font=("Arial", 12)).grid(column=1, row=0, padx=xx, pady=yy)

    button_voltage = ctk.CTkButton(button_frame, text="voltage", command=plot_voltage, state="disabled")
    button_voltage.grid(column=0, row=5, padx=xx, pady=yy, sticky=ctk.W)
    buttons_list.append(button_voltage)

    button_current = ctk.CTkButton(button_frame, text="current", command=plot_current, state="disabled")
    button_current.grid(column=0, row=6, padx=xx, pady=yy, sticky=ctk.W)
    buttons_list.append(button_current)

    button_temperature = ctk.CTkButton(button_frame, text="temperature", command=plot_temperature, state="disabled")
    button_temperature.grid(column=0, row=7, padx=xx, pady=yy, sticky=ctk.W)
    buttons_list.append(button_temperature)

    button_accelerometer_x = ctk.CTkButton(button_frame, text="accelerometer_x", command=plot_accelerometer_x, state="disabled")
    button_accelerometer_x.grid(column=1, row=5, padx=xx, pady=yy, sticky=ctk.W)
    buttons_list.append(button_accelerometer_x)

    button_accelerometer_y = ctk.CTkButton(button_frame, text="accelerometer_y", command=plot_accelerometer_y, state="disabled")
    button_accelerometer_y.grid(column=1, row=6, padx=xx, pady=yy, sticky=ctk.W)
    buttons_list.append(button_accelerometer_y)

    button_accelerometer_z = ctk.CTkButton(button_frame, text="accelerometer_z", command=plot_accelerometer_z, state="disabled")
    button_accelerometer_z.grid(column=1, row=7, padx=xx, pady=yy, sticky=ctk.W)
    buttons_list.append(button_accelerometer_z)

    button_gps_mode = ctk.CTkButton(button_frame, text="gps_mode", command=plot_gps_mode, state="disabled")
    button_gps_mode.grid(column=2, row=5, padx=xx, pady=yy, sticky=ctk.W)
    buttons_list.append(button_gps_mode)

    button_altitude = ctk.CTkButton(button_frame, text="altitude", command=plot_altitude, state="disabled")
    button_altitude.grid(column=2, row=6, padx=xx, pady=yy, sticky=ctk.W)
    buttons_list.append(button_altitude)

    button_TWD97_x = ctk.CTkButton(button_frame, text="TWD97_x", command=plot_TWD97_x, state="disabled")
    button_TWD97_x.grid(column=2, row=7, padx=xx, pady=yy, sticky=ctk.W)
    buttons_list.append(button_TWD97_x)

    button_TWD97_y = ctk.CTkButton(button_frame, text="TWD97_y", command=plot_TWD97_y, state="disabled")
    button_TWD97_y.grid(column=2, row=8, padx=xx, pady=yy, sticky=ctk.W)
    buttons_list.append(button_TWD97_y)

    button_TWD97_xy = ctk.CTkButton(button_frame, text="TWD97_xy", command=plot_TWD97_xy, state="disabled")
    button_TWD97_xy.grid(column=2, row=9, padx=xx, pady=yy, sticky=ctk.W)
    buttons_list.append(button_TWD97_xy)

    button_open_all = ctk.CTkButton(button_frame, text="Open All Plots", command=open_all_plots, fg_color="#2894FF", state="disabled")
    button_open_all.grid(column=0, row=11, padx=xx, pady=yy, sticky=ctk.W + ctk.S)
    buttons_list.append(button_open_all)

    button_close_all = ctk.CTkButton(button_frame, text="Close All Plots", command=close_all_plots, fg_color="#003060", state="disabled")
    button_close_all.grid(column=0, row=12, padx=xx, pady=yy, sticky=ctk.W + ctk.S)
    buttons_list.append(button_close_all)

    button_exit = ctk.CTkButton(button_frame, text="EXIT", command=close_program, fg_color="grey", text_color="black")
    button_exit.grid(column=2, row=12, padx=xx, pady=yy, sticky=ctk.E + ctk.S)

    root.mainloop()

# 呼叫 create_gui() 來啟動 GUI
create_gui()
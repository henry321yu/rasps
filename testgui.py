import os
import configparser
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from pyproj import Transformer
import customtkinter as ctk
from tkinter import filedialog



def create_gui():
    global root, folder_path_label, text_log

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

    Folder_button=ctk.CTkButton(root, text="Select Folder", font=("Arial", 12)).pack(padx=xx, pady=yy)

    # 顯示資料夾路徑的 Label
    folder_path_label = ctk.CTkLabel(root, text="No folder selected", font=("Arial", 12))
    folder_path_label.pack(pady=yy)

    # Log 紀錄框
    log_frame = ctk.CTkFrame(root)
    log_frame.pack(pady=yy, fill='both', expand=True)

    # 添加滾動條
    text_log = ctk.CTkTextbox(log_frame, width=400, height=100)
    text_log.pack(side='left', fill='both', expand=True)
    
    # 顯示資料夾路徑的 Label
    label = ctk.CTkLabel(root, text="", font=("Arial", 12)).pack(pady=0)

    
    text_label = ctk.CTkLabel(root, text="").pack(padx=0, pady=0)

    # 繪圖按鈕區域
    button_frame = ctk.CTkFrame(root)
    button_frame.pack(expand=True)
    root.grid_columnconfigure(0, weight=1)

    # 添加 plot 按鈕
    ctk.CTkLabel(button_frame, text="Select plot", font=("Arial", 12)).grid(column=1,row=0,padx=xx, pady=yy)

    ctk.CTkButton(button_frame, text="voltage").grid(column=0,row=5, padx=xx, pady=yy, sticky=ctk.W)
    ctk.CTkButton(button_frame, text="current").grid(column=0,row=6, padx=xx, pady=yy, sticky=ctk.W)
    ctk.CTkButton(button_frame, text="temperature").grid(column=0,row=7, padx=xx, pady=yy, sticky=ctk.W)
    
    ctk.CTkButton(button_frame, text="accelerometer_x").grid(column=1,row=5, padx=xx, pady=yy, sticky=ctk.W)
    ctk.CTkButton(button_frame, text="accelerometer_y").grid(column=1,row=6, padx=xx, pady=yy, sticky=ctk.W)
    ctk.CTkButton(button_frame, text="accelerometer_z").grid(column=1,row=7, padx=xx, pady=yy, sticky=ctk.W)

    ctk.CTkButton(button_frame, text="gps_mode").grid(column=2,row=5, padx=xx, pady=yy, sticky=ctk.W)
    ctk.CTkButton(button_frame, text="altitude").grid(column=2,row=6, padx=xx, pady=yy, sticky=ctk.W)
    ctk.CTkButton(button_frame, text="TWD97_x").grid(column=2,row=7, padx=xx, pady=yy, sticky=ctk.W)
    ctk.CTkButton(button_frame, text="TWD97_y").grid(column=2,row=8, padx=xx, pady=yy, sticky=ctk.W)
    ctk.CTkButton(button_frame, text="TWD97_xy").grid(column=2,row=9, padx=xx, pady=yy, sticky=ctk.W)
    
    ctk.CTkButton(button_frame, text="Open All Plots").grid(column=0,row=11, padx=xx, pady=yy, sticky=ctk.S+ctk.E)
    ctk.CTkButton(button_frame, text="Close All Plots").grid(column=0,row=12, padx=xx, pady=yy, sticky=ctk.S+ctk.E)
    ctk.CTkButton(button_frame, text="EXIT", fg_color="grey", text_color="black").grid(column=0,row=13, padx=xx, pady=yy, sticky=ctk.W+ctk.S)
    
    # # 上方選擇資料夾的按鈕
    # ctk.CTkButton(button_frame, text="Select Folder", command=select_folder, font=("Arial", 12)).grid(column=0,row=13, padx=xx, pady=yy, sticky=ctk.W+ctk.S)

    root.mainloop()

# 呼叫 create_gui() 來啟動 GUI
create_gui()
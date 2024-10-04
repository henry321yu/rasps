import tkinter as tk
import os

# 初始化 GUI
root = tk.Tk()
root.title("Log Viewer")

# 创建 Text 组件来显示日志
log_text = tk.Text(root, height=20, width=50)
log_text.pack()

def log_message(message):
    log_text.insert(tk.END, message + "\n")
    log_text.see(tk.END)  # 自动滚动到最新的消息

def read_files(folder_path):
    log_message(f"Reading all .txt files from {folder_path}...")
    try:
        for filename in os.listdir(folder_path):
            if filename.endswith(".txt"):
                log_message(f"Processing file: {filename}")
                # 读取文件的逻辑...
                # 假设我们读取了一些数据，这里只做一个示例
                with open(os.path.join(folder_path, filename), 'r') as f:
                    data = f.read()
                log_message(f"Finished processing {filename}.")
    except Exception as e:
        log_message(f"Error reading files: {str(e)}")

# 示例文件夹路径
folder_path = r"C:\Users\弘銘\Desktop\shower\log data"

# 读取文件并显示日志
read_files(folder_path)

# 启动主循环
root.mainloop()

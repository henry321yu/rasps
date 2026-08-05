import serial
import time
import configparser
import os
from serial.tools import list_ports

CONFIG_FILE = "config.ini"

def create_config():
    # 若 config.ini 檔案不存在，則創建一個
    config = configparser.ConfigParser()
    config['CONFIGURE'] = {
        'COM_PORT': 'COM3',      # 預設 COM 埠
        'BAUD_RATE': '115200'    # 預設波特率
    }
    
    with open(CONFIG_FILE, 'w') as configfile:
        configfile.write("# Please enter the COM port and baudrate ...\n")
        config.write(configfile)
        print(f"Config file {CONFIG_FILE} created with default settings, please set COM port and baudrate in the file ...")        
        print("\n")
        list_available_ports()  # 列出當前可用的 COM 埠
        print("\n")

def read_config():
    # 讀取 config.ini 檔案，若不存在則創建
    if not os.path.exists(CONFIG_FILE):
        create_config()
        input()  
        return None         
    
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    
    # 從配置檔讀取 COM 埠與波特率
    com_port = config['CONFIGURE'].get('COM_PORT')
    baud_rate = config['CONFIGURE'].getint('BAUD_RATE')
    
    print(f"Using COM Port: {com_port}, Baud Rate: {baud_rate}")
    print("\n")
    return com_port, baud_rate

def list_available_ports():
    ports = list_ports.comports()  # 從 list_ports.comports() 獲取串口資訊
    if ports:
        print("Available COM ports:")
        for port in ports:
            # 確認每個 port 是 ListPortInfo 對象，才能安全地訪問 device 和 description
            if hasattr(port, 'device') and hasattr(port, 'description'):
                print(f"- {port.device} : {port.description}")
            else:
                print(f"- {port}")  # 如果不是預期的對象，則簡單輸出
    else:
        print("No available COM ports detected ... please check connection ...")

def setup():
    try:
        com_port, baud_rate = read_config()  # 從INI檔讀取設定
    except:
        return None    
    try:
        # 嘗試建立串口連接
        ser = serial.Serial(com_port, baud_rate, timeout=1)
        print("Serial port opened successfully, reading ...")
        time.sleep(1)  # 等待串口連接        
        return ser
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        print("\n")
        list_available_ports()  # 列出當前可用的 COM 埠
        print("\n")
        print("Please check config.ini and your port setting ...")
        input() 
        return None    

def loop(ser):
    while True:
        # 從HC-12接收數據
        if ser.in_waiting > 0:
            incoming_data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            print(incoming_data, end='')

        time.sleep(0.001)  # 調整延遲時間以符合通訊需求

if __name__ == "__main__":
    ser = setup()
    if ser is not None:  # 確保串口成功打開
        try:
            loop(ser)
        except KeyboardInterrupt:
            print("\nProgram terminated.")
        finally:
            ser.close()  # 確保在退出時關閉串口
            print("Serial port closed.")

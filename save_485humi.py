from pymodbus.client.sync import ModbusSerialClient
import time
from datetime import datetime

# =========================
# 串口設定 (樹莓派)
# =========================
port = '/dev/ttyUSB0'  # USB-RS485 或 UART
baudrate = 9600
parity = 'N'
stopbits = 1
bytesize = 8
timeout = 1

# =========================
# Modbus 設定
# =========================
unit_id = 1         # 從站地址
register_temp = 6   # 溫度寄存器
register_humi = 7   # 濕度寄存器

# =========================
# 建立 Modbus RTU client
# =========================
client = ModbusSerialClient(
    method='rtu',
    port=port,
    baudrate=baudrate,
    parity=parity,
    stopbits=stopbits,
    bytesize=bytesize,
    timeout=timeout
)

if not client.connect():
    print(f"無法連線到 {port}")
    exit()

# =========================
# 產生檔名 (以程式執行時間)
# =========================
now = datetime.now()
filename = now.strftime("humi_%y%m%d%H%M.txt")  # humi_2603261812.txt
print(f"數據將儲存至: {filename}")

# 開啟檔案寫入模式
file = open(filename, "w")
file.write("時間,溫度,濕度\n")  # 標題行，可省略

print("開始讀取並儲存溫濕度...\n")

# =========================
# 讀取循環
# =========================
try:
    while True:
        try:
            # 讀取溫度
            result_temp = client.read_holding_registers(address=register_temp, count=1, unit=unit_id)
            temp_value = None
            if not result_temp.isError():
                raw_temp = result_temp.registers[0]
                temp_value = raw_temp / 100.0

            # 讀取濕度
            result_humi = client.read_holding_registers(address=register_humi, count=1, unit=unit_id)
            humi_value = None
            if not result_humi.isError():
                raw_humi = result_humi.registers[0]
                humi_value = raw_humi / 100.0

            # 如果讀取成功，就寫入檔案
            if temp_value is not None and humi_value is not None:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-4]  # 顯示到百分之一秒
                line = f"{timestamp},{temp_value:.2f},{humi_value:.2f}\n"
                file.write(line)
                file.flush()  # 立即寫入檔案
                print(line.strip())

        except Exception:
            continue

        time.sleep(1)  # 每秒讀取一次

finally:
    client.close()
    file.close()
    print("Modbus 連線已關閉，檔案已儲存")
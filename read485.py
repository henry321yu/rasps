from pymodbus.client.sync import ModbusSerialClient
import time

# =========================
# 串口設定
# =========================
port = 'COM11'       # 改成你的 COM
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

print("開始讀取溫濕度...\n")

# =========================
# 讀取循環
# =========================
try:
    while True:
        try:
            # 讀取溫度
            result_temp = client.read_holding_registers(address=register_temp, count=1, unit=unit_id)
            if result_temp.isError():
                # print("讀取溫度失敗")
                temp_value = None
            else:
                raw_temp = result_temp.registers[0]
                temp_value = raw_temp / 100.0  # 轉換成實際溫度
              
            # 讀取濕度
            result_humi = client.read_holding_registers(address=register_humi, count=1, unit=unit_id)
            if result_humi.isError():
                # print("讀取濕度失敗")
                humi_value = None
            else:
                raw_humi = result_humi.registers[0]
                humi_value = raw_humi / 100.0  # 轉換成百分比

            # 顯示結果
            if temp_value is not None and humi_value is not None:
                print(f"溫度: {temp_value:.2f} °C\t濕度: {humi_value:.2f} %")
            # else:
                # print("讀取失敗，重試中...")

        except Exception as e:
            # print("讀取過程發生錯誤:", e)
            continue

        # time.sleep(1)  # 每秒讀取一次

finally:
    client.close()
    print("Modbus 連線已關閉")
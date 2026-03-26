from pymodbus.client.sync import ModbusSerialClient
import time

# =========================
# 串口設定
# =========================
PORT = 'COM8'          # 改成你的 COM
PARITY = 'N'
STOPBITS = 1
BYTESIZE = 8
TIMEOUT = 1

# 常見波特率
BAUDRATES = [9600]      # 可增加 [9600, 19200, 38400]

# 掃描範圍
UNIT_IDS = range(1, 2)      # 從站地址常見 1~4
REGISTERS = range(6, 8)     # 常見寄存器 6=溫度, 7=濕度

# 將原始數值轉換為實際溫度/濕度
def convert_value(raw):
    """
    將寄存器讀出的整數值轉換成浮點數
    0      -> 0.00
    10000  -> 100.00
    """
    return raw / 100.0

print("開始掃描 RS485 Modbus 設備...\n")

try:
    while True:
        for baud in BAUDRATES:
            client = ModbusSerialClient(
                port=PORT,
                baudrate=baud,
                parity=PARITY,
                stopbits=STOPBITS,
                bytesize=BYTESIZE,
                timeout=TIMEOUT,
                method='rtu'
            )

            if not client.connect():
                print(f"無法連線，波特率 {baud} 跳過")
                continue

            for unit in UNIT_IDS:
                for addr in REGISTERS:
                    try:
                        result = client.read_holding_registers(address=addr, count=1, unit=unit)
                        if not result.isError():
                            raw_value = result.registers[0]
                            converted = convert_value(raw_value)
                            if addr == 6:
                                print(f"溫度 : {converted:.2f} °C", end='\t')
                            elif addr == 7:
                                print(f"濕度 : {converted:.2f} %")
                    except Exception as e:
                        # 可選擇顯示錯誤訊息或忽略
                        print(f"[Unit {unit}] 讀取寄存器 {addr} 發生錯誤: {e}")

            client.close()

        # 掃描間隔，可依需求調整
        # time.sleep(2)

except KeyboardInterrupt:
    print("\n掃描中止")
from pymodbus.client.sync import ModbusSerialClient
import time

# 串口設定
port = 'COM8'  # 改成你的 COM
parity = 'N'
stopbits = 1
bytesize = 8
timeout = 1

# 常見波特率
baudrates = [9600, 19200, 38400]

# 掃描範圍
unit_ids = range(1, 5)        # 從站地址常見 1~4
registers = range(0, 128)     # 常見寄存器 0~127

print("開始掃描 RS485 Modbus 設備...\n")

for baud in baudrates:
    print(f"嘗試波特率: {baud}")
    client = ModbusSerialClient(
        port=port,
        baudrate=baud,
        parity=parity,
        stopbits=stopbits,
        bytesize=bytesize,
        timeout=timeout,
        method='rtu'
    )

    if not client.connect():
        print(f"無法連線，波特率 {baud} 跳過")
        continue

    for unit in unit_ids:
        for addr in registers:
            try:
                result = client.read_holding_registers(address=addr, count=1, unit=unit)
                if not result.isError():
                    value = result.registers[0]
                    print(f"回應: unit={unit}, address={addr}, value={value}")
            except Exception as e:
                # 可以忽略錯誤
                pass

    client.close()
    print(f"波特率 {baud} 掃描完成\n")

print("掃描結束")
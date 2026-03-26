from pymodbus.client import ModbusSerialClient

client = ModbusSerialClient(
    port='COM8',        # 改成你的 COM
    baudrate=9600,
    timeout=1,
    parity='N',
    stopbits=1,
    bytesize=8
)

if not client.connect():
    print("連線失敗")
    exit()

result = client.read_holding_registers(address=0, count=1, device_id=1)

if not result.isError():
    raw = result.registers[0]
    humidity = raw / 10.0
    print(f"濕度: {humidity}%")
else:
    print("讀取失敗:", result)

client.close()
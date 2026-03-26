from pymodbus.client.sync import ModbusSerialClient as ModbusClient

client = ModbusClient(
    port='COM8',
    baudrate=9600,
    parity='N',
    stopbits=1,
    bytesize=8,
    timeout=3
)
client.connect()

if not client.connect():
    print("連線失敗")
    exit()

slave_id = 0x01

try:
    result = client.read_holding_registers(address=0, count=2, unit=slave_id)

    if result.isError():
        print("讀取失敗")
    else:
        temperature = result.registers[0] / 10.0
        humidity = result.registers[1] / 10.0
        print(f"溫度: {temperature} °C, 濕度: {humidity} %")
finally:
    client.close()
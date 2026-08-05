from pymodbus.client.sync import ModbusSerialClient

client = ModbusSerialClient(
    method='rtu',
    port='/dev/ttyUSB0',
    baudrate=9600,
    parity='N',
    stopbits=1,
    bytesize=8,
    timeout=1
)

client.connect()

OLD_ID = 1
NEW_ID = 2   # ← 你要改成幾

result = client.write_register(
    address=0x000F,
    value=NEW_ID,
    unit=OLD_ID
)

if result.isError():
    print("❌ 修改失敗")
else:
    print("✅ 修改成功，請斷電重啟")

client.close()

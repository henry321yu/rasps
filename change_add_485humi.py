from pymodbus.client.sync import ModbusSerialClient

client = ModbusSerialClient(
    method='rtu',
    port='/dev/ttyUSB0',   # 改成你的
    baudrate=9600,
    parity='N',
    stopbits=1,
    bytesize=8,
    timeout=1
)

client.connect()

OLD_ID = 1
NEW_ID = 2

# 正確位址（手冊寫死）
ADDR_REGISTER = 0x000F

result = client.write_register(
    address=ADDR_REGISTER,
    value=NEW_ID,
    unit=OLD_ID
)

if result.isError():
    print("❌ 修改失敗")
else:
    print("✅ 修改成功，請斷電重啟")

client.close()
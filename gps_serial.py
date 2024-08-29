import serial

ser=serial.Serial('COM36',9600)

while True:
    byteCount=ser.inWaiting()
    s=ser.read(byteCount)
    print(s)
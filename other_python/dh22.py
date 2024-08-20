# Complete project details at https://RandomNerdTutorials.com
from machine import I2C, Pin
from machine_i2c_lcd import I2cLcd
from time import sleep
import dht

i2c=I2C(0,sda=Pin(0),scl=Pin(1),freq=400000)
ADDR=0x27
lcd=I2cLcd(i2c,ADDR,2,16)

sensor = dht.DHT22(Pin(14))

while True:
  try:
    sleep(0.01)
    sensor.measure()
    temp = sensor.temperature()
    hum = sensor.humidity()
    temp_f = temp * (9/5) + 32.0
    print('Temperature: %3.1f C' %temp,'Humidity: %3.1f %%' %hum)
    lcd.clear()
    lcd.move_to(0,0)
    lcd.putstr(str(temp))
    lcd.move_to(5,0)
    lcd.putstr("C")
    lcd.move_to(0,1)
    lcd.putstr(str(hum))
    lcd.move_to(5,1)
    lcd.putstr("%")
  except OSError as e:
    print('Failed to read sensor.')

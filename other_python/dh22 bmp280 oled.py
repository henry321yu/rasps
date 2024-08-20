# Source: Electrocredible.com, Language: MicroPython

from machine import Pin,I2C
from bmp280 import *
from ssd1306 import SSD1306_I2C
from time import sleep
import dht

sensor = dht.DHT22(Pin(14))

WIDTH =128                     
HEIGHT= 64
i2c=I2C(0,scl=Pin(1),sda=Pin(0),freq=1000000)
oled = SSD1306_I2C(WIDTH,HEIGHT,i2c)
bmp = BMP280(i2c)
bmp.use_case(BMP280_CASE_INDOOR)

while True:
    try:
        sleep(0.005)
        sensor.measure()
        temp = sensor.temperature()-1.8  # cal
        hum = sensor.humidity()-12  # cal
        temp_f = temp * (9/5) + 32.0
       
        pressure=bmp.pressure+618  # cal
        btemp=bmp.temperature

        oled.text("Temperature:", 0, 0)
        oled.text(str(temp), 20, 10)
        oled.text("C", 70, 10)
        oled.text("humidity:", 0, 20)
        oled.text(str(hum), 20, 30)
        oled.text("%", 70, 30)
        oled.text("Pressure:", 0, 40)
        oled.text(str(pressure), 20, 50)
        oled.text(" Pa", 80, 50)
        oled.show()
        oled.fill(0)
        print('Temperature: %3.1f C' %temp,'Humidity: %3.1f %%' %hum,'Pressure: %3.1f Pa' %pressure)
        
        
    except OSError as e:
        print('Failed to read sensor.')


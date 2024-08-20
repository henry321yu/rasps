# Source: Electrocredible.com, Language: MicroPython

from machine import Pin,I2C
from machine import ADC, Pin
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

adc = ADC(Pin(26));
Vin = 3.3;
Vout = 0;
R1 = 995;
R2 = 0;

while True:
    try:
        sleep(0.005)
        sensor.measure()   #took so fuckin long
        temp = sensor.temperature()-1.8  # cal
        hum = sensor.humidity()-12  # cal
        temp_f = temp * (9/5) + 32.0
       
        pressure=bmp.pressure+618  # cal
        btemp=bmp.temperature
        
        Vout = (adc.read_u16()* Vin) / 65536.0;
        R2 = R1 * ((Vin / Vout) - 1)/1000;
        ntc10=0.000001310376*R2**6 - 0.0001344363*R2**5+ 0.005704832*R2**4 - 0.1302487*R2**3 + 1.758585*R2**2 - 15.24158*R2 + 86.897;
        
        print('ntc10: %3.3f degree' %ntc10,'R2: %3.3f ohm' %R2,'Temperature: %3.1f C' %temp,'Humidity: %3.1f %%' %hum,'Pressure: %3.1f Pa' %pressure)
        

        oled.text("Temperature:", 0, 0)
#         oled.text(str(temp), 20, 10)
        oled.text(str(ntc10), 20, 10)
        oled.text("C", 70, 10)
        oled.text("humidity:", 0, 20)
        oled.text(str(hum), 20, 30)
        oled.text("%", 70, 30)
        oled.text("Pressure:", 0, 40)
        oled.text(str(pressure), 20, 50)
        oled.text(" Pa", 80, 50)
        oled.show()
        oled.fill(0)
        
    except OSError as e:
        print('Failed to read sensor.')



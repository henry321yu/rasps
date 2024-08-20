from machine import I2C, Pin
from machine_i2c_lcd import I2cLcd
#from time import sleep, sleep_ms
import time

i2c=I2C(0,sda=Pin(0),scl=Pin(1),freq=400000)
ADDR=0x27
lcd=I2cLcd(i2c,ADDR,2,16)

pin1 = Pin(21, Pin.IN, Pin.PULL_UP)
pin2 = Pin(20, Pin.IN, Pin.PULL_UP)
led = Pin(16, Pin.OUT)
position=0
now=0
setd=0.09

def phaseA(pin):
    #print("A Interrupt Detected")
    global position
    if(pin1.value()==1):
        if(pin2.value()==0):
            position = position + setd
        else :
            position = position - setd
    
    if(pin1.value()==0):
        if(pin2.value()==1):
            position = position + setd
        else :
            position = position - setd
    #print(position)
    
def phaseB(pin):
    #print("B Interrupt Detected")
    global position
    if(pin2.value()==1):
        if(pin1.value()==1):
            position = position + setd
        else :
            position = position - setd
     
    if(pin2.value()==0):
        if(pin1.value()==0):
            position = position + setd
        else :
            position = position - setd   
    #print(position)

pin1.irq(trigger=Pin.IRQ_FALLING, handler=phaseA)
pin2.irq(trigger=Pin.IRQ_FALLING, handler=phaseB)
lcd.clear()
lcd.move_to(0,0)
lcd.putstr("position(meter):")
lcd.move_to(0,1)
lcd.putstr(str(position))
lcd.move_to(10,1)
lcd.putstr("m")

while True:
    if(now!=position):
        lcd.clear()
        lcd.move_to(0,0)
        lcd.putstr("position(meter):")
        lcd.move_to(0,1)
        lcd.putstr(str(position))
        lcd.move_to(10,1)
        lcd.putstr("m")
    
        now=position
        print(position)
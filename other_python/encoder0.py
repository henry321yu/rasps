# Source: Electrocredible.com, Language: MicroPython
from machine import Pin
import time
pin1 = Pin(21, Pin.IN, Pin.PULL_UP)
pin2 = Pin(20, Pin.IN, Pin.PULL_UP)
led = Pin(16, Pin.OUT)
position=0
setd=1.5

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
    
    print(position)
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
    
    print(position)

pin1.irq(trigger=Pin.IRQ_FALLING, handler=phaseA)
pin2.irq(trigger=Pin.IRQ_FALLING, handler=phaseB)
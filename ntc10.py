from time import sleep
from machine import Pin,I2C
from machine import ADC, Pin


adc = ADC(Pin(26));
# adc = 92;
Vin = 3.3;
Vout = 0;
R1 = 995;
R2 = 0;

while True:
    sleep(0.005)
    
    Vout = (adc.read_u16()* Vin) / 65536;
    R2 = R1 * ((Vin / Vout) - 1)/1000;
    ntc10=0.000001310376*R2**6 - 0.0001344363*R2**5+ 0.005704832*R2**4 - 0.1302487*R2**3 + 1.758585*R2**2 - 15.24158*R2 + 86.897;
    Vout = (adc.read_u16()* Vin)
    
    print('Vout: %3.1f ohm' %Vout,'ntc10: %3.3f degree' %ntc10,'R2: %3.1f ohm' %R2)
            

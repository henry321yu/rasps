from machine import Pin, ADC, I2C, UART
from ssd1306 import SSD1306_I2C
import framebuf,sys,time

WIDTH =128 
HEIGHT= 64

i2c= I2C(0,scl=Pin(9),sda=Pin(8),freq=1000000)  # start I2C on I2C1 (GPIO 26/27)
i2c_addr = [hex(ii) for ii in i2c.scan()] # get I2C address in hex format
print("I2C Address:{}".format(i2c_addr[0])) # I2C device address

oled = SSD1306_I2C(WIDTH,HEIGHT,i2c)


# 設定UART
uart = UART(0, tx=Pin(16), rx=Pin(17), baudrate = 9600, parity = None, bits = 8, stop = 1, timeout = 600)

# 設定ADC通道
current_adc = ADC(Pin(26))  # GP26
voltage_adc = ADC(Pin(27))  # GP27

# 參數
V_REF = 3.228  # 參考電壓
ADC_RES = 65535  # 16-bit ADC 解析度

# ACS712 參數
SENSITIVITY = 0.185  # ACS712-05B 的靈敏度是 185 mV/A
OFFSET = V_REF / 2  # 中心電壓 (電源電壓的一半)

r1=7.52 #k ohm
r2=30.16 #k ohm
vv=(r1+r2)/r1

maxbat=13.2

def read_current():
    adc_value = current_adc.read_u16()
    voltage = (adc_value / ADC_RES) * V_REF
    voltage = (voltage - OFFSET) 
    current = voltage / SENSITIVITY-0.3
    if current<0.01:
        current=0
    return current

def read_voltage():
    adc_value = voltage_adc.read_u16()
    voltage = (adc_value / ADC_RES) * V_REF *vv  # 考慮分壓
    return voltage

def update_display(current, voltage):
    oled.fill(0)
    oled.text(str(round(voltage,3)), 0, 0)#x,y
    oled.text("v", 80, 0) 
    oled.text(str(round(current,3)), 0, 20)
    oled.text("A", 80, 20)
    oled.text(str(round(persent,3)), 0, 40)
    oled.text("%", 80, 40)
    oled.show()

def send_uart(current, voltage, persent):
    uart.write(str(round(current,3)).encode('utf-8'))
    uart.write(b",")
    uart.write(str(round(voltage,3)).encode('utf-8'))
    uart.write(b",")
    uart.write(str(round(persent,3)).encode('utf-8'))
    uart.write(b"\n")
    
# 設置 HC-12 模塊的 UART
uart = UART(0, 9600)  # 默認速率是 9600 bps
set_pin = Pin(18, Pin.OUT)  # 假設SET引腳連接到GP15
set_pin.value(0)  # 拉低SET引腳進入AT模式
time.sleep(0.1)  # 等待模塊穩定
uart.write("AT+B115200\r\n") # 將波特率設置為 115200 bps
time.sleep(0.1)  # 等待模塊回應
uart = UART(0, 115200)  # 115200 bps
time.sleep(0.1)  # 等待模塊回應
uart.write("AT+B115200\r\n") # 將波特率設置為 115200 bps
time.sleep(0.1)  # 等待模塊回應
uart.write("AT+C087\r\n")# 將頻道設置為 87
time.sleep(0.1)  # 等待模塊回應
uart.write("AT+P8\r\n")
time.sleep(0.1)  # 等待模塊回應
# 檢查回應
if uart.any():
    message = uart.read()
    print(message.decode('utf-8'))
            
set_pin.value(1)

while True:
    current = read_current()
    voltage = read_voltage()
    persent=voltage/maxbat*100
    update_display(current, voltage)
    send_uart(current, voltage, persent)
    
    print(f"current :{current:.3f} A,voltage :{voltage:.3f} V,{persent:.3} %")
    time.sleep(0.1)

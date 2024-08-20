# from gpiozero import CPUTemperature
from time import sleep, strftime, time

# cpu = CPUTemperature()

with open("C:/Users/sgrc-325/Desktop/py/logger.csv","a") as log:
    while True:
#         temp = cpu.temperature
#         log.write("{0},{1}\n".format(strftime("%Y-%m-%d %H:%M:%S"),str(temp)))
        log.write("{0}\n".format(strftime("%Y-%m-%d %H:%M:%S")))
#         time.sleep(0,01)
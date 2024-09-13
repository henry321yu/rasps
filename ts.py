from time import sleep, strftime, time
from datetime import datetime
import os

current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
print("current time :", current_datetime)
log_folder = r'C:\Users\sgrc-325\Desktop\py\log'
# log_folder = r'C:\Users\弘銘\Desktop\WFH\git\log'
# log_folder = r'/home/rasp3/Desktop/log'
log_filename = f'logger_T_{current_datetime}.csv'
log_filepath = os.path.join(log_folder, log_filename)

if not os.path.exists(log_folder):
    os.makedirs(log_folder)
    
log = open(log_filepath, 'w+', encoding="utf8")

while True:
    current_datetime = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    print(current_datetime) 
    log.write(current_datetime + '\n')
    log.flush()
    sleep(1)


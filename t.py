from time import sleep, strftime, time
from datetime import datetime

while True:
    current_datetime = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    print(current_datetime)
    sleep(1)


import socket
from time import sleep, strftime, time
import os
from IPython.display import clear_output
from datetime import datetime


HEADERSIZE = 10

# HOST = "104.116.45.14"  # office pc
# HOST = "104.116.45.98"  # fly pc
HOST = "0.0.0.0"  # my pc
PORT = 5566

current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
print("current time :",current_datetime)
log_folder = r'C:\Users\sgrc-325\Desktop\py\log'
log_filename = f'logger_PC_{current_datetime}.csv'
log_filepath = os.path.join(log_folder, log_filename)

if not os.path.exists(log_folder):
    os.makedirs(log_folder)

print('Waiting for connection...')
log = open(log_filepath, 'w+', encoding="utf8")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()

    s, address = s.accept()
    print(f"Connection from {address} has been established.")
    
    full_msg = ''
    new_msg = True
    while True:
        msg = s.recv(1024)
        full_msg = msg.decode("utf-8")
        if len(full_msg)<10:
            new_msg = False
            print(f"False")

#         print(len(full_msg))
        clear_output(wait=True)
        print(full_msg)
        log.write(full_msg)
        
log.close()
s.close()

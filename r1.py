import socket
from time import sleep, strftime, time


HEADERSIZE = 10

HOST = "140.116.45.98"  # office pc
PORT = 5566

print('Waiting for connection...')
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
        print(full_msg)
        
s.close()
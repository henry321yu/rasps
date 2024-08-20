import socket
import time

HEADERSIZE = 10

HOST = "140.116.45.98"  # office pc
PORT = 5566

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))

while True:
    msg = "Welcome"
    msg = f"{len(msg):<{HEADERSIZE}}"+msg

    s.send(bytes(msg,"utf-8"))

    while True:
        time.sleep(1)
        msg = f"The time is {time.time()}"
        msg = f"{len(msg):<{HEADERSIZE}}"+msg

        print(msg)

        s.send(bytes(msg,"utf-8"))
import socket  #接收端
from time import sleep, strftime, time
import os
from IPython.display import clear_output
from datetime import datetime
import matplotlib.pyplot as plt

HEADERSIZE = 10

# HOST = "104.116.45.14"  # office pc
# HOST = "104.116.45.98"  # fly pc
HOST = "0.0.0.0"  # my pc
PORT = 5566

current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
print("current time :", current_datetime)
log_folder = r'C:\Users\sgrc-325\Desktop\py\log'
# log_folder = r'C:\Users\弘銘\Desktop\WFH\git\log'
log_filename = f'logger_PC_{current_datetime}.csv'
log_filepath = os.path.join(log_folder, log_filename)

if not os.path.exists(log_folder):
    os.makedirs(log_folder)

print('Waiting for connection...')
log = open(log_filepath, 'w+', encoding="utf8")

# Initialize plot
plt.ion()
fig, ax = plt.subplots()
x_data = []
y_data = []

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()

    conn, address = s.accept()
    print(f"Connection from {address} has been established.")
    
    full_msg = ''
    new_msg = True
    while True:
        msg = conn.recv(1024)
        full_msg = msg.decode("utf-8")

        if len(full_msg) < 10:
            new_msg = False
#             print(f"False")

        # Extract latitude and longitude from the message
        parts = full_msg.split('\t')
        if len(parts) > 8:
            try:
                lat = float(parts[6])
                lon = float(parts[7])
                x_data.append(lon)
                y_data.append(lat)
                
                # Update plot
                ax.clear()
                ax.scatter(x_data, y_data, c='blue', marker='.')
                ax.set_xlabel('Longitude')
                ax.set_ylabel('Latitude')
                ax.set_title('GPS Coordinates')
                plt.draw()
                plt.pause(0.01)
                
                # Log the message
                log.write(full_msg)
                log.flush()
                clear_output(wait=True)
                print(full_msg, end='')
            except ValueError:
                # Handle any value conversion errors
                pass

log.close()
conn.close()

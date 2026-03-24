import os
import serial
import threading
import time
from pyubx2 import UBXReader
from datetime import datetime, timedelta

# ===== folder =====
folder = "f9p"
os.makedirs(folder, exist_ok=True)

now = datetime.now()

gnss_filename = os.path.join(folder, f"gnss_log_{now.strftime('%y%m%d%H%M%S')}.ubx")
humi_filename = os.path.join(folder, f"humi_log_{now.strftime('%y%m%d%H%M%S')}.txt")

print("GNSS:", gnss_filename)
print("HUMI:", humi_filename)

# ===== shared variable =====
latest_humidity = None
lock = threading.Lock()

start_time = time.time()

# ===== serial init function =====
def init_gnss():
    ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
    return ser, UBXReader(ser)

def init_humi():
    ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
    time.sleep(2)
    return ser

ser_gnss, ubr = init_gnss()
ser_humi = init_humi()


# =========================
# GNSS THREAD
# =========================
def gnss_thread():
    global ser_gnss, ubr

    with open(gnss_filename, 'ab') as f:

        while True:
            try:
                raw, parsed = ubr.read()

                if raw:
                    f.write(raw)
                    f.flush()

                if parsed and parsed.identity == "NAV-PVT":
                    elapsed = time.time() - start_time
                    size_mb = f.tell() / (1024 * 1024)

                    dt = datetime(parsed.year, parsed.month, parsed.day,
                                  parsed.hour, parsed.min, parsed.second)
                    local_time = dt + timedelta(hours=8)

                    hAcc = parsed.hAcc / 1000
                    vAcc = parsed.vAcc / 1000

                    with lock:
                        hum = latest_humidity

                    print(f"""
Uptime: {elapsed:.1f} sec
Gnss File size: {size_mb:.2f} MB
Time: {local_time}
Satellites: {parsed.numSV}
HAcc: {hAcc:.3f} m
VAcc: {vAcc:.3f} m
Humidity: {hum} %
""")

            except OSError as e:
                msg = str(e)

                # 👉 忽略 F9P 常見 false-ready error
                if "returned no data" in msg:
                    continue

                print("GNSS Error:", e)

                # 👉 reconnect
                try:
                    ser_gnss.close()
                except:
                    pass

                time.sleep(1)
                ser_gnss, ubr = init_gnss()

            except Exception as e:
                print("GNSS Fatal Error:", e)
                time.sleep(1)


# =========================
# HUMIDITY THREAD
# =========================
def humidity_thread():
    global ser_humi, latest_humidity

    save_interval = 1.0
    last_save_time = 0

    with open(humi_filename, 'a') as f:

        while True:
            try:
                line = ser_humi.readline().decode(errors='ignore').strip()

                if line:
                    try:
                        hum = float(line)

                        with lock:
                            latest_humidity = hum

                        now_time = time.time()

                        if now_time - last_save_time >= save_interval:
                            last_save_time = now_time

                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-4]
                            f.write(f"{timestamp},{hum:.2f}\n")
                            f.flush()

                    except:
                        pass

            except OSError as e:
                print("HUMI Error:", e)

                # 👉 reconnect USB serial
                try:
                    ser_humi.close()
                except:
                    pass

                time.sleep(1)
                ser_humi = init_humi()

            except Exception as e:
                print("HUMI Fatal Error:", e)
                time.sleep(1)


# =========================
# start threads
# =========================
t1 = threading.Thread(target=gnss_thread, daemon=True)
t2 = threading.Thread(target=humidity_thread, daemon=True)

t1.start()
t2.start()

t1.join()
t2.join()
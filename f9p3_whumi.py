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

# ===== serial =====
ser_gnss = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
ubr = UBXReader(ser_gnss)

ser_humi = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
time.sleep(2)

# ===== shared variable =====
latest_humidity = None
lock = threading.Lock()

start_time = time.time()


# =========================
# GNSS THREAD (原本幾乎不動)
# =========================
def gnss_thread():
    global latest_humidity

    with open(gnss_filename, 'ab') as f:

        while True:
            try:
                raw, parsed = ubr.read()

                if raw:
                    f.write(raw)
                    f.flush()

                # GNSS print（加濕度顯示）
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

            except Exception as e:
                print("GNSS Error:", e)


# =========================
# HUMIDITY THREAD (1Hz)
# =========================
def humidity_thread():
    global latest_humidity

    save_interval = 1.0   # 👉 控制儲存頻率（秒）
    last_save_time = 0

    with open(humi_filename, 'a') as f:

        while True:
            try:
                line = ser_humi.readline().decode().strip()

                if line:
                    try:
                        hum = float(line)

                        with lock:
                            latest_humidity = hum

                        # ===== 控制寫入頻率 =====
                        now_time = time.time()

                        if now_time - last_save_time >= save_interval:
                            last_save_time = now_time

                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-4]
                            f.write(f"{timestamp},{hum:.2f}\n")
                            f.flush()

                    except:
                        pass

            except Exception as e:
                print("HUMI Error:", e)


# =========================
# start threads
# =========================
t1 = threading.Thread(target=gnss_thread, daemon=True)
t2 = threading.Thread(target=humidity_thread, daemon=True)

t1.start()
t2.start()

t1.join()
t2.join()
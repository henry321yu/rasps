import os
import serial
import threading
import time
from pyubx2 import UBXReader
from datetime import datetime, timedelta
from serial.tools import list_ports

# =========================
# VID / PID
# =========================
GNSS_VID = 0x1546
GNSS_PID = 0x01A9

HUMI_VID = 0x0403
HUMI_PID = 0x6001

# ===== folder =====
folder = "f9p"
os.makedirs(folder, exist_ok=True)

now = datetime.now()

gnss_filename = os.path.join(folder, f"gnss_log_{now.strftime('%y%m%d%H%M%S')}.ubx")
humi_filename = os.path.join(folder, f"humi_log_{now.strftime('%y%m%d%H%M%S')}.txt")

print("GNSS:", gnss_filename)
print("HUMI:", humi_filename)

latest_humidity = None
lock = threading.Lock()
start_time = time.time()

# =========================
# FIND PORT BY VID/PID
# =========================
def find_port(vid, pid):
    for p in list_ports.comports():
        if p.vid == vid and p.pid == pid:
            return p.device
    return None

# =========================
# INIT GNSS
# =========================
def init_gnss():
    while True:
        port = find_port(GNSS_VID, GNSS_PID)
        if port:
            try:
                ser = serial.Serial(port, 115200, timeout=1)
                print(f"[GNSS] Connected: {port}")
                return ser, UBXReader(ser)
            except Exception as e:
                print("[GNSS] Open failed:", e)

        print("[GNSS] Waiting device...")
        time.sleep(1)

# =========================
# INIT HUMI
# =========================
def init_humi():
    while True:
        port = find_port(HUMI_VID, HUMI_PID)
        if port:
            try:
                ser = serial.Serial(port, 115200, timeout=1)
                print(f"[HUMI] Connected: {port}")
                time.sleep(2)
                return ser
            except Exception as e:
                print("[HUMI] Open failed:", e)

        print("[HUMI] Waiting device...")
        time.sleep(1)

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
                if "returned no data" in str(e):
                    continue

                print("[GNSS] Error:", e)

                try:
                    ser_gnss.close()
                except:
                    pass

                time.sleep(1)
                ser_gnss, ubr = init_gnss()

            except Exception as e:
                print("[GNSS] Fatal:", e)
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
                if "returned no data" in str(e):
                    continue

                print("[HUMI] Error:", e)

                try:
                    ser_humi.close()
                except:
                    pass

                time.sleep(1)
                ser_humi = init_humi()

            except Exception as e:
                print("[HUMI] Fatal:", e)
                time.sleep(1)

# =========================
# START
# =========================
t1 = threading.Thread(target=gnss_thread, daemon=True)
t2 = threading.Thread(target=humidity_thread, daemon=True)

t1.start()
t2.start()

t1.join()
t2.join()
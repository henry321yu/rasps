import socket
import threading
import math
import cv2
import numpy as np
import time
from collections import deque
from flask import Flask, Response, jsonify, request
from datetime import datetime

# CAMERA_TITLE = "Raspberry Pi Camera"
# ADXL_TITLE = "ADXL355 Real-time Vibration"
CAMERA_TITLE = "Real-time Camera"
ADXL_TITLE = "Real-time Accelerometer"

# ==================================================
# 初始預設設定與控制範圍
# ==================================================
# 1. 網頁圖表與攝影機更新頻率 (毫秒)
DEFAULT_UPDATE_INTERVAL_MS = 1000
MIN_UPDATE_INTERVAL_MS = 10
MAX_UPDATE_INTERVAL_MS = 60000

# 2. 每 N 筆做一次平均
DEFAULT_AVERAGE_N = 5
MIN_AVERAGE_N = 1
MAX_AVERAGE_N = 10000

# 3. 網頁顯示總筆數 (最大值調整至 30000)
DEFAULT_DISPLAY_POINTS = 1000
MIN_DISPLAY_POINTS = 100
MAX_DISPLAY_POINTS = 30000

# 全域動態控制變數 (執行時會變動)
global_interval_sec = DEFAULT_UPDATE_INTERVAL_MS / 1000.0
global_average_n = DEFAULT_AVERAGE_N
global_display_points = DEFAULT_DISPLAY_POINTS

# ==================================================
# UDP 設定與 Data Buffers
# ==================================================
ADXL_PORT = 2870
IMAGE_PORT = 2885

MAX_POINTS = max(30000, MAX_DISPLAY_POINTS)

t_buf = deque(maxlen=MAX_POINTS)
ax_buf = deque(maxlen=MAX_POINTS)
ay_buf = deque(maxlen=MAX_POINTS)
az_buf = deque(maxlen=MAX_POINTS)
vector_buf = deque(maxlen=MAX_POINTS)

latest_frame = None

# ==================================================
# ADXL355 & Camera UDP Receivers
# ==================================================
def adxl_receiver():
    global global_average_n
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", ADXL_PORT))
    print(f"Listening ADXL355 UDP {ADXL_PORT}")

    count = 0
    sum_ax = sum_ay = sum_az = 0.0

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            message = data.decode("utf-8")
            parts = message.split(",")

            if len(parts) == 5:
                ax, ay, az = float(parts[1]), float(parts[2]), float(parts[3])
                sum_ax += ax
                sum_ay += ay
                sum_az += az
                count += 1

                if count >= global_average_n:
                    avg_ax, avg_ay, avg_az = sum_ax / count, sum_ay / count, sum_az / count
                    avg_vector = math.sqrt(avg_ax**2 + avg_ay**2 + avg_az**2)
                    current_time = datetime.now().strftime('%H:%M:%S.%f')[:-4]

                    t_buf.append(current_time)
                    ax_buf.append(avg_ax)
                    ay_buf.append(avg_ay)
                    az_buf.append(avg_az)
                    vector_buf.append(avg_vector)

                    count = 0
                    sum_ax = sum_ay = sum_az = 0.0
        except Exception:
            pass

# ==================================================
# Camera UDP Receiver
# ==================================================
def camera_receiver():
    global latest_frame
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", IMAGE_PORT))
    print(f"Listening Camera UDP {IMAGE_PORT}")

    while True:
        try:
            data, addr = sock.recvfrom(65535)
            np_arr = np.frombuffer(data, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is not None:
                latest_frame = frame
        except Exception:
            pass

# ==================================================
# 客戶端監控系統 (Client Monitor System)
# ==================================================
clients_lock = threading.Lock()
clients_info = {}

def client_monitor_thread():
    """背景監控：每 10 秒印出一次連線列表，並清除逾時的連線"""
    while True:
        time.sleep(10)
        now = time.time()
        active_list = []
        
        with clients_lock:
            for ip in list(clients_info.keys()):
                info = clients_info[ip]
                is_streaming = info["streams"] > 0
                
                # 若超過 10 秒沒來拉取 /data 且沒在看影像，視為斷線
                is_active = (now - info["last_seen"]) < 10
                
                if not is_streaming and not is_active:
                    print(f"\n[-] 客戶端離線: {ip}")
                    del clients_info[ip]
                else:
                    status = "觀看影像中" if is_streaming else "背景更新數據中"
                    cmd_info = f" | 最新指令: {info['last_command']}" if info['last_command'] else ""
                    active_list.append(f"  - IP: {ip} [{status}]{cmd_info}")
        
        # 如果有活躍客戶端，印出清單
        if active_list:
            print("\n=== 目前已連線客戶端 ===")
            for line in active_list:
                print(line)
            print("========================")

# ==================================================
# Flask Web Server
# ==================================================
app = Flask(__name__)

# ----- 請求攔截器 (記錄與追蹤指令) -----
@app.before_request
def track_client_connect():
    ip = request.remote_addr
    path = request.path
    query = request.query_string.decode('utf-8')
    full_command = f"{path}?{query}" if query else path
    
    with clients_lock:
        if ip not in clients_info:
            clients_info[ip] = {"last_seen": time.time(), "streams": 0, "last_command": None}
            print(f"\n[+] 新客戶端連線: {ip}")
        
        clients_info[ip]["last_seen"] = time.time()
        
        # 即時捕捉並印出使用者的設定指令 (排除 /data 和 /camera 這種常態請求)
        if path.startswith('/set_'):
            clients_info[ip]["last_command"] = full_command
            print(f"\n[*] 客戶端 {ip} 發出指令: {full_command}")
            
        elif path == '/camera':
            clients_info[ip]["streams"] += 1
            print(f"\n[>] 客戶端 {ip} 載入影像串流 (當前開啓 {clients_info[ip]['streams']} 個)")

@app.teardown_request
def track_client_disconnect(exception=None):
    ip = request.remote_addr
    path = request.path
    
    # 若瀏覽器斷開影像串流，則將串流計數 -1
    if path == '/camera':
        with clients_lock:
            if ip in clients_info:
                clients_info[ip]["streams"] = max(0, clients_info[ip]["streams"] - 1)
                print(f"\n[<] 客戶端 {ip} 停止觀看影像串流")


# --------------------------------------------------
# API: 動態控制項
# --------------------------------------------------
@app.route("/set_interval")
def set_interval():
    global global_interval_sec
    try:
        ms = int(request.args.get('val', DEFAULT_UPDATE_INTERVAL_MS))
        ms = max(MIN_UPDATE_INTERVAL_MS, min(MAX_UPDATE_INTERVAL_MS, ms)) 
        global_interval_sec = ms / 1000.0
        return jsonify({"status": "ok", "val": ms})
    except:
        return jsonify({"status": "error"}), 400

@app.route("/set_average")
def set_average():
    global global_average_n
    try:
        val = int(request.args.get('val', DEFAULT_AVERAGE_N))
        global_average_n = max(MIN_AVERAGE_N, min(MAX_AVERAGE_N, val)) 
        return jsonify({"status": "ok", "val": global_average_n})
    except:
        return jsonify({"status": "error"}), 400

@app.route("/set_display")
def set_display():
    global global_display_points
    try:
        val = int(request.args.get('val', DEFAULT_DISPLAY_POINTS))
        global_display_points = max(MIN_DISPLAY_POINTS, min(MAX_DISPLAY_POINTS, val)) 
        return jsonify({"status": "ok", "val": global_display_points})
    except:
        return jsonify({"status": "error"}), 400

# --------------------------------------------------
# Main Page
# --------------------------------------------------
@app.route("/")
def index():
    html = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sensor Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        *, *::before, *::after { box-sizing: border-box; }
        :root { --bg-color: #0f172a; --card-bg: #1e293b; --text-main: #f8fafc; --border-color: #334155; --accent: #38bdf8; --item-bg: #111827; }
        body { margin: 0; background-color: var(--bg-color); color: var(--text-main); font-family: 'Segoe UI', Arial, sans-serif; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        .header { padding: 1rem 1.5rem; background: var(--card-bg); border-bottom: 1px solid var(--border-color); display: flex; align-items: center; flex-wrap: wrap; gap: 1.5rem; }
        .header h1 { margin: 0; font-size: 1.5rem; color: var(--accent); letter-spacing: 1px; white-space: nowrap; }
        .controls-container { display: flex; flex-wrap: wrap; gap: 1rem; margin-left: auto; }
        .control-item { display: flex; align-items: center; gap: 0.6rem; background: var(--item-bg); padding: 0.5rem 1rem; border-radius: 8px; border: 1px solid var(--border-color); }
        .control-item label { font-size: 0.85rem; color: #94a3b8; font-weight: 600; white-space: nowrap; }
        .control-item input[type="range"] { cursor: pointer; accent-color: var(--accent); width: 100px; }
        .control-item input[type="number"] { width: 75px; background: rgba(255,255,255,0.05); color: var(--accent); border: 1px solid var(--border-color); border-radius: 4px; padding: 2px 6px; font-weight: bold; text-align: center; font-size: 0.9rem; }
        .control-item input[type="number"]:focus { outline: none; border-color: var(--accent); background: rgba(255,255,255,0.1); }
        .container { display: flex; flex: 1; padding: 1rem; gap: 1rem; min-height: 0; }
        .panel { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; display: flex; flex-direction: column; flex: 1; min-width: 0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
        .panel-header { padding: 0.8rem 1.2rem; border-bottom: 1px solid var(--border-color); font-weight: 600; background: rgba(0,0,0,0.15); }
        .panel-content { flex: 1; display: flex; align-items: center; justify-content: center; padding: 0.5rem; position: relative; min-height: 0; }
        .charts-container { display: flex; flex-direction: column; width: 100%; height: 100%; gap: 0.5rem; align-items: stretch; }
        .chart-wrapper { flex: 1 1 0; position: relative; min-height: 0; min-width: 0; background: var(--item-bg); border-radius: 6px; padding: 5px; border: 1px solid var(--border-color); width: 100%; }
        .camera-img { max-width: 100%; max-height: 100%; object-fit: contain; border-radius: 8px; }
        canvas { width: 100% !important; height: 100% !important; }
        @media(max-width: 1200px) { .controls-container { margin-left: 0; width: 100%; } }
        @media(max-width: 900px) { .container { flex-direction: column; overflow-y: auto; } body { overflow: auto; height: auto; } .panel { height: 60vh; flex: none; } .control-item { width: 100%; justify-content: space-between; } .control-item input[type="range"] { flex: 1; margin: 0 1rem; } }
    </style>
</head>
<body>

    <div class="header">
        <h1>Control Center</h1>
        <div class="controls-container">
            <div class="control-item">
                <label>Rate (ms)</label>
                <input type="range" id="rateSlider" min="MIN_INTERVAL_MS" max="MAX_INTERVAL_MS" step="50">
                <input type="number" id="rateNum" min="MIN_INTERVAL_MS" max="MAX_INTERVAL_MS" step="10">
            </div>
            <div class="control-item">
                <label>Avg N</label>
                <input type="range" id="avgSlider" min="MIN_AVG_N" max="MAX_AVG_N" step="1">
                <input type="number" id="avgNum" min="MIN_AVG_N" max="MAX_AVG_N" step="1">
            </div>
            <div class="control-item">
                <label>Display Pts</label>
                <input type="range" id="ptsSlider" min="MIN_DISP_PTS" max="MAX_DISP_PTS" step="100">
                <input type="number" id="ptsNum" min="MIN_DISP_PTS" max="MAX_DISP_PTS" step="100">
            </div>
        </div>
    </div>

    <div class="container">
        <div class="panel">
            <div class="panel-header">CAM_TITLE</div>
            <div class="panel-content">
                <img id="cameraImg" class="camera-img" src="/camera" alt="Live Camera Feed">
            </div>
        </div>
        <div class="panel">
            <div class="panel-header">ADXL_TITLE</div>
            <div class="panel-content charts-container">
                <div class="chart-wrapper"><canvas id="chartVector"></canvas></div>
                <div class="chart-wrapper"><canvas id="chartAX"></canvas></div>
                <div class="chart-wrapper"><canvas id="chartAY"></canvas></div>
                <div class="chart-wrapper"><canvas id="chartAZ"></canvas></div>
            </div>
        </div>
    </div>

    <script>
        Chart.defaults.color = '#94a3b8';
        function createChart(ctxId, titleText, lineColor, showXAxis) {
            let ctx = document.getElementById(ctxId).getContext("2d");
            return new Chart(ctx, {
                type: "line",
                data: { labels: [], datasets: [{ label: titleText, data: [], borderColor: lineColor, borderWidth: 1.2, pointRadius: 0, tension: 0.1 }] },
                options: {
                    animation: false, responsive: true, maintainAspectRatio: false, normalized: true,
                    layout: { padding: { top: 0, bottom: 0, right: 20, left: 5 } },
                    plugins: { legend: { display: false }, title: { display: true, text: titleText, color: lineColor, align: 'start', padding: { top: 2, bottom: 2 } } },
                    scales: {
                        x: { display: showXAxis, grid: { color: '#334155' }, ticks: { maxRotation: 0, align: 'inner', autoSkip: false, callback: function(val, index, ticks) {
                            let total = ticks.length; let step = Math.max(1, Math.floor(total / 2)); 
                            if (index === 0 || index === total - 1 || index % step === 0) return this.getLabelForValue(val);
                            return null; 
                        } } },
                        y: { display: true, grid: { color: '#334155' }, ticks: { font: { size: 10 } } }
                    }
                }
            });
        }

        let chartVector = createChart("chartVector", "Vector Magnitude", "#facc15", false);
        let chartAX = createChart("chartAX", "AX", "#f87171", false);
        let chartAY = createChart("chartAY", "AY", "#4ade80", false);
        let chartAZ = createChart("chartAZ", "AZ", "#38bdf8", true);

        function updateADXL() {
            fetch("/data").then(r => r.json()).then(d => {
                chartVector.data.labels = d.t; chartVector.data.datasets[0].data = d.vector; chartVector.update();
                chartAX.data.labels = d.t; chartAX.data.datasets[0].data = d.ax; chartAX.update();
                chartAY.data.labels = d.t; chartAY.data.datasets[0].data = d.ay; chartAY.update();
                chartAZ.data.labels = d.t; chartAZ.data.datasets[0].data = d.az; chartAZ.update();
            }).catch(err => console.error("Error fetching data:", err));
        }

        let updateIntervalId = null;

        function setupControl(sliderId, numId, minVal, maxVal, defaultVal, apiEndpoint, callback) {
            const slider = document.getElementById(sliderId); const num = document.getElementById(numId);
            function apply(val, source) {
                let v = parseInt(val); if (isNaN(v)) return;
                v = Math.max(minVal, Math.min(maxVal, v));
                if (source === 'slider') { num.value = v; } else { slider.value = v; num.value = v; }
                fetch(`${apiEndpoint}?val=${v}`).catch(e => console.log(e));
                if (callback) callback(v);
            }
            slider.addEventListener('input', () => apply(slider.value, 'slider'));
            num.addEventListener('change', () => apply(num.value, 'num'));
            apply(defaultVal, 'init');
        }

        setupControl('rateSlider', 'rateNum', MIN_INTERVAL_MS, MAX_INTERVAL_MS, DEFAULT_INTERVAL_MS, '/set_interval', (newInterval) => {
            if (updateIntervalId) clearInterval(updateIntervalId);
            updateIntervalId = setInterval(updateADXL, newInterval);
        });
        setupControl('avgSlider', 'avgNum', MIN_AVG_N, MAX_AVG_N, DEFAULT_AVG_N, '/set_average', null);
        setupControl('ptsSlider', 'ptsNum', MIN_DISP_PTS, MAX_DISP_PTS, DEFAULT_DISP_PTS, '/set_display', null);

        const camImg = document.getElementById("cameraImg");
        camImg.onerror = function() {
            console.warn("Camera disconnected. Reconnecting...");
            setTimeout(() => { camImg.src = "/camera?t=" + new Date().getTime(); }, 2000);
        };
    </script>
</body>
</html>
"""
    html = html.replace("CAM_TITLE", CAMERA_TITLE).replace("ADXL_TITLE", ADXL_TITLE)
    html = html.replace("DEFAULT_INTERVAL_MS", str(DEFAULT_UPDATE_INTERVAL_MS))
    html = html.replace("MIN_INTERVAL_MS", str(MIN_UPDATE_INTERVAL_MS)).replace("MAX_INTERVAL_MS", str(MAX_UPDATE_INTERVAL_MS))
    html = html.replace("DEFAULT_AVG_N", str(DEFAULT_AVERAGE_N))
    html = html.replace("MIN_AVG_N", str(MIN_AVERAGE_N)).replace("MAX_AVG_N", str(MAX_AVERAGE_N))
    html = html.replace("DEFAULT_DISP_PTS", str(DEFAULT_DISPLAY_POINTS))
    html = html.replace("MIN_DISP_PTS", str(MIN_DISPLAY_POINTS)).replace("MAX_DISP_PTS", str(MAX_DISPLAY_POINTS))
    return html

# --------------------------------------------------
# ADXL API
# --------------------------------------------------
@app.route("/data")
def data():
    return jsonify({
        "t": list(t_buf)[-global_display_points:],
        "ax": list(ax_buf)[-global_display_points:],
        "ay": list(ay_buf)[-global_display_points:],
        "az": list(az_buf)[-global_display_points:],
        "vector": list(vector_buf)[-global_display_points:]
    })

# --------------------------------------------------
# MJPEG Camera Stream
# --------------------------------------------------
@app.route("/camera")
def camera():
    def generate():
        last_send_time = 0
        try:
            while True:
                current_time = time.time()
                time_since_last = current_time - last_send_time
                if time_since_last >= global_interval_sec:
                    if latest_frame is not None:
                        ret, jpeg = cv2.imencode(".jpg", latest_frame)
                        if ret:
                            yield (b"--frame\r\n" b"Content-Type:image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
                    last_send_time = time.time()
                    continue
                sleep_time = global_interval_sec - (time.time() - last_send_time)
                if sleep_time > 0:
                    time.sleep(min(sleep_time, 0.05))
        except GeneratorExit:
            pass # 這裡留空，斷線紀錄統一交給 @app.teardown_request 處理
        except Exception:
            pass

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

# ==================================================
# Main
# ==================================================
if __name__ == "__main__":
    threading.Thread(target=adxl_receiver, daemon=True).start()
    threading.Thread(target=camera_receiver, daemon=True).start()
    
    # 啟動「客戶端監控」背景執行緒
    threading.Thread(target=client_monitor_thread, daemon=True).start()

    print(f"""
======================================
 ADXL355 + Camera Web Monitor
 Open: http://0.0.0.0:6969
 
 Server Started! Waiting for clients...
======================================
""")

    from waitress import serve
    serve(app, host="0.0.0.0", port=6969, threads=6)
import socket
import threading
import math
import cv2
import numpy as np
import time
import uuid
from collections import deque
from flask import Flask, Response, jsonify, request
from datetime import datetime
import itertools

SERVER_RUN_ID = str(uuid.uuid4())

# CAMERA_TITLE = "Raspberry Pi Camera"
# ADXL_TITLE = "ADXL355 Real-time Vibration"
CAMERA_TITLE = "Real-time Camera"
ADXL_TITLE = "Real-time Accelerometer"

# ==================================================
# 初始預設設定與控制範圍
# ==================================================
DEFAULT_UPDATE_INTERVAL_MS = 500
MIN_UPDATE_INTERVAL_MS = 50
SLIDER_MAX_UPDATE_INTERVAL_MS = 5000
MAX_UPDATE_INTERVAL_MS = 10000

DEFAULT_AVERAGE_N = 5
MIN_AVERAGE_N = 1
SLIDER_MAX_AVERAGE_N = 500
MAX_AVERAGE_N = 60000

DEFAULT_DISPLAY_POINTS = 1000
MIN_DISPLAY_POINTS = 100
SLIDER_MAX_DISPLAY_POINTS = 6000
MAX_DISPLAY_POINTS = 300000

PEAK_OFFSET_VALUE = 1.0

# ==================================================
# UDP 設定與 Data Buffers
# ==================================================
ADXL_PORT = 2870
IMAGE_PORT = 2885

MAX_BUFFER_LEN = 300000 

data_buf = deque(maxlen=MAX_BUFFER_LEN)
global_packet_count = 0
latest_frame = None
latest_jpeg = None

# ==================================================
# ADXL355 & Camera UDP Receivers
# ==================================================
def adxl_receiver():
    global global_packet_count
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", ADXL_PORT))
    print(f"Listening ADXL355 UDP {ADXL_PORT}")

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            message = data.decode("utf-8")
            parts = message.split(",")

            if len(parts) == 5:
                ax, ay, az = float(parts[1]), float(parts[2]), float(parts[3])
                current_time = datetime.now().strftime('%H:%M:%S.%f')[:-4]
                
                global_packet_count += 1
                data_buf.append((global_packet_count, current_time, ax, ay, az))
        except Exception:
            pass

def camera_receiver():
    global latest_jpeg
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # 加大作業系統底層的接收緩衝區，避免封包瞬間湧入被丟棄 (設定為 1MB)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)
    sock.bind(("0.0.0.0", IMAGE_PORT))
    print(f"Listening Camera UDP {IMAGE_PORT}")

    while True:
        try:
            # 直接接收 UDP 封包
            data, addr = sock.recvfrom(65535)
            
            # [大幅優化] 前端直接收！
            # 樹莓派送來的 data 已經是合法的 JPEG byte array
            # 完全不透過 OpenCV 解碼與編碼，直接存起來準備推送給網頁！
            if len(data) > 0:
                latest_jpeg = data
                
        except Exception as e:
            pass

# ==================================================
# 客戶端監控系統 (Client Monitor System)
# ==================================================
clients_lock = threading.Lock()
clients_info = {}

def client_monitor_thread():
    while True:
        time.sleep(10)
        now = time.time()
        active_list = []
        
        with clients_lock:
            for cid in list(clients_info.keys()):
                info = clients_info[cid]
                is_streaming = info["streams"] > 0
                is_active = (now - info["last_seen"]) < 10
                
                if not is_streaming and not is_active:
                    print(f"\n[-] 客戶端離線: ID={cid[:8]} ({info['ip']})")
                    del clients_info[cid]
                else:
                    status = "觀看影像中" if is_streaming else "背景更新數據中"
                    cmd_info = f" | 最新指令: {info['last_command']}" if info['last_command'] else ""
                    active_list.append(f"  - ID: {cid[:8]} (IP: {info['ip']}) [{status}]{cmd_info}")
        if active_list:
            print("\n=== 目前已連線客戶端 ===")
            for line in active_list:
                print(line)
            print("========================")

# ==================================================
# Flask Web Server
# ==================================================
app = Flask(__name__)

@app.before_request
def track_client_connect():
    client_id = request.args.get('client_id', request.remote_addr)
    ip = request.remote_addr
    path = request.path
    query = request.query_string.decode('utf-8')
    full_command = f"{path}?{query}" if query else path
    
    with clients_lock:
        if client_id not in clients_info:
            clients_info[client_id] = {
                "ip": ip,
                "last_seen": time.time(), 
                "streams": 0, 
                "last_command": None,
                "interval_sec": DEFAULT_UPDATE_INTERVAL_MS / 1000.0,
                "avg_n": DEFAULT_AVERAGE_N,
                "display_pts": DEFAULT_DISPLAY_POINTS
            }
            print(f"\n[+] 新客戶端連線: ID={client_id[:8]} ({ip})")
        
        clients_info[client_id]["last_seen"] = time.time()
        
        if path.startswith('/set_'):
            clients_info[client_id]["last_command"] = full_command
            print(f"\n[*] 客戶端 ID={client_id[:8]} 發出指令: {full_command}")
            
        elif path == '/camera':
            clients_info[client_id]["streams"] += 1
            print(f"\n[>] 客戶端 ID={client_id[:8]} 載入影像串流 (當前開啓 {clients_info[client_id]['streams']} 個)")

@app.teardown_request
def track_client_disconnect(exception=None):
    client_id = request.args.get('client_id', request.remote_addr)
    path = request.path
    
    if path == '/camera':
        with clients_lock:
            if client_id in clients_info:
                clients_info[client_id]["streams"] = max(0, clients_info[client_id]["streams"] - 1)
                print(f"\n[<] 客戶端 ID={client_id[:8]} 停止觀看影像串流")

@app.route("/set_interval")
def set_interval():
    client_id = request.args.get('client_id', request.remote_addr)
    try:
        ms = int(request.args.get('val', DEFAULT_UPDATE_INTERVAL_MS))
        ms = max(MIN_UPDATE_INTERVAL_MS, min(MAX_UPDATE_INTERVAL_MS, ms)) 
        with clients_lock:
            if client_id in clients_info:
                clients_info[client_id]["interval_sec"] = ms / 1000.0
        return jsonify({"status": "ok", "val": ms})
    except:
        return jsonify({"status": "error"}), 400

@app.route("/set_average")
def set_average():
    client_id = request.args.get('client_id', request.remote_addr)
    try:
        val = int(request.args.get('val', DEFAULT_AVERAGE_N))
        val = max(MIN_AVERAGE_N, min(MAX_AVERAGE_N, val)) 
        with clients_lock:
            if client_id in clients_info:
                clients_info[client_id]["avg_n"] = val
        return jsonify({"status": "ok", "val": val})
    except:
        return jsonify({"status": "error"}), 400

@app.route("/set_display")
def set_display():
    client_id = request.args.get('client_id', request.remote_addr)
    try:
        val = int(request.args.get('val', DEFAULT_DISPLAY_POINTS))
        val = max(MIN_DISPLAY_POINTS, min(MAX_DISPLAY_POINTS, val)) 
        with clients_lock:
            if client_id in clients_info:
                clients_info[client_id]["display_pts"] = val
        return jsonify({"status": "ok", "val": val})
    except:
        return jsonify({"status": "error"}), 400

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
        .controls-container { display: flex; flex-wrap: wrap; gap: 1rem; margin-left: auto; align-items: center; }
        .control-item { display: flex; align-items: center; gap: 0.6rem; background: var(--item-bg); padding: 0.5rem 1rem; border-radius: 8px; border: 1px solid var(--border-color); }
        .control-item label { font-size: 0.85rem; color: #94a3b8; font-weight: 600; white-space: nowrap; }
        .control-item input[type="range"] { cursor: pointer; accent-color: var(--accent); width: 100px; }
        .control-item input[type="number"] { width: 75px; background: rgba(255,255,255,0.05); color: var(--accent); border: 1px solid var(--border-color); border-radius: 4px; padding: 2px 6px; font-weight: bold; text-align: center; font-size: 0.9rem; }
        .control-item input[type="number"]:focus { outline: none; border-color: var(--accent); background: rgba(255,255,255,0.1); }
        
        .record-btn { background: transparent; color: #f8fafc; border: 1px solid #475569; border-radius: 6px; padding: 4px 12px; cursor: pointer; display: flex; align-items: center; gap: 6px; font-size: 0.9rem; font-weight: bold; transition: all 0.2s; }
        .record-btn:hover { background: rgba(255, 255, 255, 0.1); }
        .record-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .record-icon { width: 12px; height: 12px; background: #ef4444; border-radius: 50%; display: inline-block; transition: all 0.2s; }
        .record-btn.recording { background: #ef4444; color: #fff; border-color: #ef4444; animation: pulse 2s infinite; }
        .record-btn.recording .record-icon { background: #fff; border-radius: 2px; }
        #recordTimer { font-family: 'Courier New', Courier, monospace; font-size: 1rem; color: #f87171; width: 55px; text-align: center; font-weight: bold; letter-spacing: 1px;}
        @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); } 70% { box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); } 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); } }
        .checkbox-group { display: flex; gap: 10px; margin-left: 5px; border-left: 1px solid #475569; padding-left: 10px; }
        .checkbox-group label { cursor: pointer; display: flex; align-items: center; gap: 4px; }

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
            
            <div class="control-item" style="border-color: rgba(239, 68, 68, 0.4);">
                <button id="recordBtn" class="record-btn">
                    <span class="record-icon"></span> <span id="btnText">錄影</span>
                </button>
                <span id="recordTimer">00:00</span>
                <div class="checkbox-group">
                    <label><input type="checkbox" id="recCam" checked> 影像</label>
                    <label><input type="checkbox" id="recChart" checked> 數據圖</label>
                </div>
            </div>

            <div class="control-item">
                <label>Rate (ms)</label>
                <input type="range" id="rateSlider" min="MIN_INTERVAL_MS" max="SLIDER_MAX_INTERVAL_MS" step="10">
                <input type="number" id="rateNum" min="MIN_INTERVAL_MS" max="MAX_INTERVAL_MS" step="10">
            </div>
            <div class="control-item">
                <label>Avg N</label>
                <input type="range" id="avgSlider" min="MIN_AVG_N" max="SLIDER_MAX_AVG_N" step="1">
                <input type="number" id="avgNum" min="MIN_AVG_N" max="MAX_AVG_N" step="1">
            </div>
            <div class="control-item">
                <label>Display Pts</label>
                <input type="range" id="ptsSlider" min="MIN_DISP_PTS" max="SLIDER_MAX_DISP_PTS" step="100">
                <input type="number" id="ptsNum" min="MIN_DISP_PTS" max="MAX_DISP_PTS" step="100">
            </div>
        </div>
    </div>
    <div class="container">
        <div class="panel">
            <div class="panel-header">CAM_TITLE</div>
            <div class="panel-content">
                <img id="cameraImg" class="camera-img" alt="Live Camera Feed">
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
        const clientId = Math.random().toString(36).substring(2, 15);

        Chart.defaults.color = '#94a3b8';
        function createChart(ctxId, titleText, lineColor, showXAxis) {
            let ctx = document.getElementById(ctxId).getContext("2d");
            return new Chart(ctx, {
                type: "line",
                data: { labels: [], datasets: [{ label: titleText, data: [], borderColor: lineColor, borderWidth: 1.2, pointRadius: 0, tension: 0 }] },
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

        let serverIsOnline = true; 
        let currentServerId = null; 

        function updateADXL() {
            fetch(`/data?client_id=${clientId}`)
                .then(r => {
                    if (!r.ok) throw new Error("Server response not ok");
                    return r.json();
                })
                .then(d => {
                    let needsCameraReset = false;

                    if (!serverIsOnline) {
                        serverIsOnline = true;
                        needsCameraReset = true;
                    }

                    if (currentServerId === null) {
                        currentServerId = d.server_id; 
                    } else if (currentServerId !== d.server_id) {
                        currentServerId = d.server_id; 
                        needsCameraReset = true;
                    }

                    if (needsCameraReset) {
                        console.log("偵測到伺服器重連或重啟，正在強制刷新影像...");
                        const camImg = document.getElementById("cameraImg");
                        camImg.src = "data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=";
                        setTimeout(() => {
                            camImg.src = `/camera?client_id=${clientId}&t=` + new Date().getTime();
                        }, 500);
                    }

                    chartVector.data.labels = d.t; chartVector.data.datasets[0].data = d.vector; chartVector.update();
                    chartAX.data.labels = d.t; chartAX.data.datasets[0].data = d.ax; chartAX.update();
                    chartAY.data.labels = d.t; chartAY.data.datasets[0].data = d.ay; chartAY.update();
                    chartAZ.data.labels = d.t; chartAZ.data.datasets[0].data = d.az; chartAZ.update();
                })
                .catch(err => {
                    if (serverIsOnline) {
                        console.warn("與伺服器失去連線，等待重連中...");
                        serverIsOnline = false;
                    }
                });
        }

        let updateIntervalId = null;

        function setupControl(sliderId, numId, minVal, maxVal, defaultVal, apiEndpoint, callback) {
            const slider = document.getElementById(sliderId); const num = document.getElementById(numId);
            function apply(val, source) {
                let v = parseInt(val); if (isNaN(v)) return;
                v = Math.max(minVal, Math.min(maxVal, v));
                
                if (source === 'slider') { 
                    num.value = v; 
                } else { 
                    slider.value = v; 
                    num.value = v; 
                }
                
                fetch(`${apiEndpoint}?client_id=${clientId}&val=${v}`).catch(e => console.log(e));
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
        camImg.src = `/camera?client_id=${clientId}`;
        camImg.onerror = function() {
            setTimeout(() => { camImg.src = `/camera?client_id=${clientId}&t=` + new Date().getTime(); }, 2000);
        };

        // ==========================================
        // 加入全包圍等距留白 (Padding) 錄製功能
        // ==========================================
        const recordBtn = document.getElementById("recordBtn");
        const recordTimer = document.getElementById("recordTimer");
        const btnText = document.getElementById("btnText");
        
        const recCam = document.getElementById("recCam");
        const recChart = document.getElementById("recChart");
        
        const chartCanvases = [
            document.getElementById("chartVector"),
            document.getElementById("chartAX"),
            document.getElementById("chartAY"),
            document.getElementById("chartAZ")
        ];

        let mediaRecorder;
        let recordedChunks = [];
        let recordIntervalId;
        let timerIntervalId;
        let startTime;
        let isRecording = false;

        const hiddenCanvas = document.createElement("canvas");
        const hiddenCtx = hiddenCanvas.getContext("2d");

        recordBtn.addEventListener("click", () => {
            if (!isRecording) {
                startRecording();
            } else {
                stopRecording();
            }
        });

        function startRecording() {
            const doCam = recCam.checked;
            const doChart = recChart.checked;

            if (!doCam && !doChart) {
                alert("請至少勾選一項要錄製的內容 (影像 或 數據圖)！");
                return;
            }

            if (doCam && (!camImg.complete || camImg.naturalWidth === 0)) {
                alert("影像尚未載入完成，請稍後再試！");
                return;
            }

            let camW = 0, camH = 0;
            let chartW = 0, chartTotalH = 0;
            let chartBoxes = []; 
            const PADDING = 20;

            if (doCam) {
                camW = camImg.naturalWidth;
                camH = camImg.naturalHeight;
            }

            if (doChart) {
                for(let cvs of chartCanvases) {
                    chartW = Math.max(chartW, cvs.width);
                    chartTotalH += cvs.height;
                    chartBoxes.push({ w: cvs.width, h: cvs.height });
                }
            }

            let totalW = PADDING;
            if (doCam) totalW += camW + PADDING;
            if (doChart) totalW += chartW + PADDING;

            let maxContentH = Math.max((doCam ? camH : 0), (doChart ? chartTotalH : 0));
            let totalH = maxContentH + PADDING * 2;

            hiddenCanvas.width = totalW;
            hiddenCanvas.height = totalH;

            let camY = PADDING;
            let chartStartY = PADDING;
            if (doCam && doChart) {
                if (camH < chartTotalH) {
                    camY = PADDING + (chartTotalH - camH) / 2;
                } else {
                    chartStartY = PADDING + (camH - chartTotalH) / 2; 
                }
            }

            recCam.disabled = true;
            recChart.disabled = true;

            recordIntervalId = setInterval(() => {
                hiddenCtx.fillStyle = '#0f172a';
                hiddenCtx.fillRect(0, 0, hiddenCanvas.width, hiddenCanvas.height);

                let startX = PADDING;

                if (doCam) {
                    if (camImg.naturalWidth > 0) {
                        hiddenCtx.drawImage(camImg, startX, camY, camW, camH);
                    }
                    startX += camW + PADDING;
                }

                if (doChart) {
                    let currentY = chartStartY;
                    for (let i = 0; i < chartCanvases.length; i++) {
                        let cvs = chartCanvases[i];
                        let box = chartBoxes[i];
                        hiddenCtx.drawImage(cvs, startX, currentY, box.w, box.h);
                        currentY += box.h; 
                    }
                }
            }, 1000 / 30);

            const stream = hiddenCanvas.captureStream(30);
            
            try {
                mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm; codecs=vp8' });
            } catch (e) {
                mediaRecorder = new MediaRecorder(stream);
            }

            recordedChunks = [];
            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) recordedChunks.push(e.data);
            };

            mediaRecorder.onstop = () => {
                const blob = new Blob(recordedChunks, { type: 'video/webm' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                
                let filePrefix = "Record";
                if (doCam && doChart) filePrefix = "Camera_And_Chart";
                else if (doCam) filePrefix = "Camera_Only";
                else filePrefix = "Chart_Only";

                const dateStr = new Date().toISOString().replace(/[:T]/g, '-').slice(0, 19);
                a.download = `${filePrefix}_${dateStr}.webm`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            };

            mediaRecorder.start();
            isRecording = true;
            
            recordBtn.classList.add("recording");
            btnText.innerText = "停止";
            
            startTime = Date.now();
            recordTimer.innerText = "00:00";
            timerIntervalId = setInterval(updateTimer, 1000);
        }

        function stopRecording() {
            mediaRecorder.stop();
            clearInterval(recordIntervalId);
            clearInterval(timerIntervalId);
            isRecording = false;
            
            recordBtn.classList.remove("recording");
            btnText.innerText = "錄影";
            recCam.disabled = false;
            recChart.disabled = false;
        }

        function updateTimer() {
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            const mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
            const secs = String(elapsed % 60).padStart(2, '0');
            recordTimer.innerText = `${mins}:${secs}`;
        }
    </script>
</body>
</html>
"""
    html = html.replace("CAM_TITLE", CAMERA_TITLE).replace("ADXL_TITLE", ADXL_TITLE)
    
    html = html.replace("DEFAULT_INTERVAL_MS", str(DEFAULT_UPDATE_INTERVAL_MS))
    html = html.replace("MIN_INTERVAL_MS", str(MIN_UPDATE_INTERVAL_MS))
    html = html.replace("SLIDER_MAX_INTERVAL_MS", str(SLIDER_MAX_UPDATE_INTERVAL_MS))
    html = html.replace("MAX_INTERVAL_MS", str(MAX_UPDATE_INTERVAL_MS))
    
    html = html.replace("DEFAULT_AVG_N", str(DEFAULT_AVERAGE_N))
    html = html.replace("MIN_AVG_N", str(MIN_AVERAGE_N))
    html = html.replace("SLIDER_MAX_AVG_N", str(SLIDER_MAX_AVERAGE_N))
    html = html.replace("MAX_AVG_N", str(MAX_AVERAGE_N))
    
    html = html.replace("DEFAULT_DISP_PTS", str(DEFAULT_DISPLAY_POINTS))
    html = html.replace("MIN_DISP_PTS", str(MIN_DISPLAY_POINTS))
    html = html.replace("SLIDER_MAX_DISP_PTS", str(SLIDER_MAX_DISPLAY_POINTS))
    html = html.replace("MAX_DISP_PTS", str(MAX_DISPLAY_POINTS))
    
    return html

# --------------------------------------------------
# ADXL API (即時動態平均化 + 穩定的錨定切塊)
# --------------------------------------------------
@app.route("/data")
def data():
    client_id = request.args.get('client_id', request.remote_addr)
    
    with clients_lock:
        if client_id in clients_info:
            avg_n = clients_info[client_id]["avg_n"]
            pts = clients_info[client_id]["display_pts"]
        else:
            avg_n = DEFAULT_AVERAGE_N
            pts = DEFAULT_DISPLAY_POINTS

    buf_len = len(data_buf)
    if buf_len == 0:
        return jsonify({"t": [], "ax": [], "ay": [], "az": [], "vector": [], "server_id": SERVER_RUN_ID})

    needed_len = pts * avg_n
    take_amount = needed_len + avg_n 
    
    # 【關鍵修復：混合策略】
    # 當需要的資料量超過或接近當前緩存量，直接使用 list() 在 C 底層複製，速度最快 (解決 avg_n=500 卡頓)
    # 當需要的資料量很少 (例如 avg_n=5)，才使用 itertools 反向抽取，節省記憶體與處理時間
    if take_amount >= buf_len:
        snapshot = list(data_buf)
    else:
        tail_reversed = list(itertools.islice(reversed(data_buf), take_amount))
        snapshot = tail_reversed[::-1]

    first_count = snapshot[0][0]
    offset = (avg_n - (first_count % avg_n)) % avg_n
    
    available_len = len(snapshot) - offset
    valid_len = available_len - (available_len % avg_n) 
    
    start_idx = offset
    if valid_len > needed_len:
        start_idx = offset + valid_len - needed_len
        
    final_slice = snapshot[start_idx : start_idx + min(valid_len, needed_len)]

    if not final_slice:
        return jsonify({"t": [], "ax": [], "ay": [], "az": [], "vector": [], "server_id": SERVER_RUN_ID})

    t_arr = [row[1] for row in final_slice]
    ax_arr = np.array([row[2] for row in final_slice])
    ay_arr = np.array([row[3] for row in final_slice])
    az_arr = np.array([row[4] for row in final_slice])

    if avg_n <= 1:
        vec_arr = np.sqrt(ax_arr**2 + ay_arr**2 + az_arr**2)
        return jsonify({
            "t": t_arr,
            "ax": ax_arr.tolist(),
            "ay": ay_arr.tolist(),
            "az": az_arr.tolist(),
            "vector": vec_arr.tolist(),
            "server_id": SERVER_RUN_ID
        })
    else:
        n_chunks = len(final_slice) // avg_n
        t_out = t_arr[avg_n-1::avg_n]
        
        ax_chunked = ax_arr.reshape(n_chunks, avg_n)
        ay_chunked = ay_arr.reshape(n_chunks, avg_n)
        az_chunked = az_arr.reshape(n_chunks, avg_n)

        ax_shifted = ax_chunked + PEAK_OFFSET_VALUE
        ay_shifted = ay_chunked + PEAK_OFFSET_VALUE
        az_shifted = az_chunked + PEAK_OFFSET_VALUE

        idx_x = np.abs(ax_shifted).argmax(axis=1)
        idx_y = np.abs(ay_shifted).argmax(axis=1)
        idx_z = np.abs(az_shifted).argmax(axis=1)

        rows = np.arange(n_chunks)
        ax_out = ax_shifted[rows, idx_x] - PEAK_OFFSET_VALUE
        ay_out = ay_shifted[rows, idx_y] - PEAK_OFFSET_VALUE
        az_out = az_shifted[rows, idx_z] - PEAK_OFFSET_VALUE
        
        vec_out = np.sqrt(ax_out**2 + ay_out**2 + az_out**2)

        return jsonify({
            "t": t_out,
            "ax": ax_out.tolist(),
            "ay": ay_out.tolist(),
            "az": az_out.tolist(),
            "vector": vec_out.tolist(),
            "server_id": SERVER_RUN_ID
        })

# --------------------------------------------------
# MJPEG Camera Stream (同步依照使用者 Rate 刷新)
# --------------------------------------------------
@app.route("/camera")
def camera():
    client_id = request.args.get('client_id', request.remote_addr)
    
    def generate():
        last_send_time = 0
        try:
            while True:
                with clients_lock:
                    interval_sec = clients_info.get(client_id, {}).get("interval_sec", DEFAULT_UPDATE_INTERVAL_MS / 1000.0)
                
                current_time = time.time()
                time_since_last = current_time - last_send_time
                
                # 若距離上次發送畫面已經超過使用者的設定時間，則發送新畫面
                if time_since_last >= interval_sec:
                    if latest_jpeg is not None:
                        yield (b"--frame\r\n" b"Content-Type:image/jpeg\r\n\r\n" + latest_jpeg + b"\r\n")
                    last_send_time = time.time()
                    continue # 【關鍵修復】送出後立刻進入下一輪評估，不要強迫睡覺
                
                # 【關鍵修復】恢復第一版的微秒級動態休眠，保證精準幀率與極速反應 Slider 變化
                sleep_time = interval_sec - (time.time() - last_send_time)
                if sleep_time > 0:
                    time.sleep(min(sleep_time, 0.05))
                    
        except GeneratorExit:
            pass 
        except Exception as e:
            pass

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

# ==================================================
# Main
# ==================================================
if __name__ == "__main__":
    threading.Thread(target=adxl_receiver, daemon=True).start()
    threading.Thread(target=camera_receiver, daemon=True).start()
    threading.Thread(target=client_monitor_thread, daemon=True).start()

    print(f"""
======================================
 ADXL355 + Camera Web Monitor
 Open: http://0.0.0.0:6969
 
 Server Started! Waiting for clients...
======================================
""")

    from waitress import serve
    serve(app, host="0.0.0.0", port=6969, threads=8)

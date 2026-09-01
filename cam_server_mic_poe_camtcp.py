import socket
import threading
import math
import cv2
import numpy as np
import time
import uuid
import queue
from collections import deque
from flask import Flask, Response, jsonify, request
from datetime import datetime
import itertools

SERVER_RUN_ID = str(uuid.uuid4())

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

DEFAULT_IMAGE_QUALITY = 70
MIN_IMAGE_QUALITY = 20
SLIDER_MAX_IMAGE_QUALITY = 100
MAX_IMAGE_QUALITY = 100

PEAK_OFFSET_VALUE = 1.0

# ==================================================
# UDP 設定與 Data Buffers
# ==================================================
ADXL_PORT = 2870
IMAGE_PORT = 2885
AUDIO_PORT = 2890
CONTROL_PORT = 2895  # [新增] 控制指令 PORT 回傳給 Sender

MAX_BUFFER_LEN = 300000 

data_buf = deque(maxlen=MAX_BUFFER_LEN)
global_packet_count = 0
latest_frame = None
latest_jpeg = None
latest_sender_ip = None # [新增] 用來記錄 Sender 的 IP 以便回傳指令

audio_subscribers = []
audio_lock = threading.Lock()

# ==================================================
# UDP Receivers
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
    global latest_jpeg, latest_sender_ip
    
    # 改為 TCP Socket Server
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("0.0.0.0", IMAGE_PORT))
    server_sock.listen(5)
    print(f"Listening Camera TCP {IMAGE_PORT}")

    def handle_client(conn, addr):
        global latest_jpeg, latest_sender_ip
        # 設定超時，若發送端卡住太久不傳資料則斷開重連
        conn.settimeout(5.0) 
        
        while True:
            try:
                # 1. 先讀取 4 bytes 的長度標頭
                header_data = b""
                while len(header_data) < 4:
                    chunk = conn.recv(4 - len(header_data))
                    if not chunk:
                        return # 客戶端已斷線
                    header_data += chunk
                
                # 解析長度
                img_size = int.from_bytes(header_data, byteorder='big')
                
                # 2. 根據長度讀取完整的 JPEG 資料
                img_data = b""
                while len(img_data) < img_size:
                    # 每次最多讀 65536 bytes，直到拼湊出完整圖片
                    chunk = conn.recv(min(img_size - len(img_data), 65536))
                    if not chunk:
                        return # 客戶端已斷線
                    img_data += chunk
                
                # 3. 成功獲取完整圖片，更新全域變數
                latest_jpeg = img_data
                latest_sender_ip = addr[0]
                
            except Exception as e:
                # 發生任何連線異常（如 Timeout, ConnectionReset）即跳出
                break
                
        conn.close()

    # 主迴圈：持續等待新的發送端連線
    while True:
        try:
            conn, addr = server_sock.accept()
            # 針對每一個連線開啟一個獨立的執行緒去處理
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
        except Exception:
            pass

def audio_receiver():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", AUDIO_PORT))
    print(f"Listening Audio UDP {AUDIO_PORT}")

    while True:
        try:
            data, addr = sock.recvfrom(8192)
            with audio_lock:
                for q in audio_subscribers:
                    # [修改] 如果 Queue 滿了，強制丟棄最舊的一包資料，確保即時性
                    if q.full():
                        try:
                            q.get_nowait()
                        except queue.Empty:
                            pass
                    q.put(data)
        except Exception:
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
                "display_pts": DEFAULT_DISPLAY_POINTS,
                "quality": DEFAULT_IMAGE_QUALITY
            }
        
        clients_info[client_id]["last_seen"] = time.time()
        
        if path.startswith('/set_'):
            clients_info[client_id]["last_command"] = full_command
            
        elif path == '/camera':
            clients_info[client_id]["streams"] += 1

@app.teardown_request
def track_client_disconnect(exception=None):
    client_id = request.args.get('client_id', request.remote_addr)
    path = request.path
    
    if path == '/camera':
        with clients_lock:
            if client_id in clients_info:
                clients_info[client_id]["streams"] = max(0, clients_info[client_id]["streams"] - 1)

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

# [新增] 設定畫質的 API
@app.route("/set_quality")
def set_quality():
    client_id = request.args.get('client_id', request.remote_addr)
    try:
        val = int(request.args.get('val', DEFAULT_IMAGE_QUALITY))
        val = max(MIN_IMAGE_QUALITY, min(MAX_IMAGE_QUALITY, val)) 
        with clients_lock:
            if client_id in clients_info:
                clients_info[client_id]["quality"] = val
        
        # 透過 UDP 傳送控制指令給 Sender
        if latest_sender_ip:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(f"QUALITY:{val}".encode(), (latest_sender_ip, CONTROL_PORT))
            except Exception as e:
                pass
                
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
        .control-item label { font-size: 0.85rem; color: #94a3b8; font-weight: 600; white-space: nowrap; cursor: pointer; }
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
        
        .panel-content { flex: 1; display: flex; padding: 0.5rem; position: relative; min-height: 0; }
        
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
                    <label><input type="checkbox" id="recAudio" checked> 音訊</label>
                </div>
            </div>

            <!-- 音訊監聽開關與音量控制 -->
            <div class="control-item" style="border-color: #4ade80;">
                <label><input type="checkbox" id="audioToggle"> 🔊 監聽音訊</label>
                <input type="range" id="audioVolume" min="0" max="1" step="0.05" value="0.8" style="width: 80px;" title="調整監聽音量">
            </div>

            <!-- [新增] 畫質控制拉桿 -->
            <div class="control-item">
                <label>Quality</label>
                <input type="range" id="qtySlider" min="MIN_QUALITY" max="SLIDER_MAX_QUALITY" step="1">
                <input type="number" id="qtyNum" min="MIN_QUALITY" max="MAX_QUALITY" step="1">
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
            <div class="panel-content" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
                <div style="flex: 1; display: flex; align-items: center; justify-content: center; min-height: 0; width: 100%;">
                    <img id="cameraImg" class="camera-img" alt="Live Camera Feed">
                </div>
                <!-- 音訊強度動態繪圖專屬區塊 -->
                <div id="audioChartWrapper" class="chart-wrapper" style="display: none; flex: 0 0 160px;">
                    <canvas id="chartAudio"></canvas>
                </div>
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

        // ==========================================
        // UI & 數據繪圖初始化
        // ==========================================
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
        
        const AUDIO_CHART_PTS = 300; 
        let chartAudio = createChart("chartAudio", "即時音訊強度 (dB)", "#a855f7", true);
        let audioDbData = new Array(AUDIO_CHART_PTS).fill(-40); // 預設底線拉低
        chartAudio.data.labels = Array.from({length: AUDIO_CHART_PTS}, (_, i) => i);
        chartAudio.data.datasets[0].data = audioDbData;
        chartAudio.update();

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
                if (source === 'slider') num.value = v; else { slider.value = v; num.value = v; }
                fetch(`${apiEndpoint}?client_id=${clientId}&val=${v}`).catch(e => console.log(e));
                if (callback) callback(v);
            }
            slider.addEventListener('input', () => apply(slider.value, 'slider'));
            num.addEventListener('change', () => apply(num.value, 'num'));
            apply(defaultVal, 'init');
        }

        // [新增] 綁定畫質控制拉桿
        setupControl('qtySlider', 'qtyNum', MIN_QUALITY, MAX_QUALITY, DEFAULT_QUALITY, '/set_quality', null);
        
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
        // 即時音訊核心 (Web Audio API)
        // ==========================================
        let audioCtx, speakerGain, recordGain, audioDest, analyser;
        let globalAudioActive = false;
        let audioAbortController = null;
        let audioChartIntervalId = null; 

        async function initAudioSystem() {
            if (audioCtx) return;
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            audioDest = audioCtx.createMediaStreamDestination(); 
            
            analyser = audioCtx.createAnalyser();
            analyser.fftSize = 2048; 
            
            speakerGain = audioCtx.createGain(); 
            speakerGain.connect(audioCtx.destination);
            
            recordGain = audioCtx.createGain();  
            recordGain.value = 1.0;
            recordGain.connect(audioDest);
            
            analyser.connect(speakerGain);
            analyser.connect(recordGain);
        }

        async function ensureAudioStreaming() {
            if (globalAudioActive) return;
            await initAudioSystem();
            
            if (audioCtx.state === 'suspended') {
                await audioCtx.resume();
            }

            globalAudioActive = true;
            audioAbortController = new AbortController();
            let nextTime = 0;
            let audioDataBuffer = new Uint8Array(0);

            try {
                const response = await fetch(`/audio_raw?client_id=${clientId}`, { signal: audioAbortController.signal });
                const reader = response.body.getReader();
                
                while (globalAudioActive) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    let newBuffer = new Uint8Array(audioDataBuffer.length + value.length);
                    newBuffer.set(audioDataBuffer, 0);
                    newBuffer.set(value, audioDataBuffer.length);

                    let numSamples = Math.floor(newBuffer.length / 2);
                    let pcm16 = new Int16Array(newBuffer.buffer, newBuffer.byteOffset, numSamples);

                    let leftover = newBuffer.length % 2;
                    audioDataBuffer = leftover > 0 ? newBuffer.slice(newBuffer.length - leftover) : new Uint8Array(0);

                    let audioBuffer = audioCtx.createBuffer(1, pcm16.length, 16000);
                    let channelData = audioBuffer.getChannelData(0);
                    
                    for (let i = 0; i < pcm16.length; i++) {
                        channelData[i] = pcm16[i] / 32768.0; 
                    }

                    let source = audioCtx.createBufferSource();
                    source.buffer = audioBuffer;
                    source.connect(analyser);

                    let currentTime = audioCtx.currentTime;
                    
                    // [修改] 動態時間校正機制
                    // 如果排程落後，給予 50ms 的基礎緩衝
                    if (nextTime < currentTime + 0.05) {
                        nextTime = currentTime + 0.05;
                    } 
                    // 如果排程已經跑到 0.3 秒以後，代表網路積壓產生了延遲
                    // 毫不猶豫把排程拉回現實，丟棄多餘的時間差，與畫面強制同步
                    else if (nextTime > currentTime + 0.3) {
                        console.log("Audio latency detected, forcing sync...");
                        nextTime = currentTime + 0.1;
                    }

                    source.start(nextTime);
                    nextTime += audioBuffer.duration;
                }
            } catch(e) {
                console.log("音訊串流中斷/結束");
            }
            globalAudioActive = false;
        }

        function stopAudioStreaming() {
            if (audioAbortController) audioAbortController.abort();
            globalAudioActive = false;
        }

        function checkAudioStop() {
            if (!document.getElementById('audioToggle').checked && !isRecording) {
                stopAudioStreaming();
            }
        }

        // 音訊 UI 控制邏輯
        document.getElementById('audioToggle').addEventListener('change', async (e) => {
            const chartWrapper = document.getElementById('audioChartWrapper'); 
            await initAudioSystem();
            if (e.target.checked) {
                chartWrapper.style.display = "block";
                chartAudio.resize(); 
                
                speakerGain.gain.value = document.getElementById('audioVolume').value;
                ensureAudioStreaming();
                
                if (audioChartIntervalId) clearInterval(audioChartIntervalId);
                audioChartIntervalId = setInterval(() => {
                    if (!analyser) return;
                    let dataArray = new Float32Array(analyser.fftSize);
                    analyser.getFloatTimeDomainData(dataArray); 
                    
                    let sumSquares = 0;
                    for (let i = 0; i < dataArray.length; i++) {
                        sumSquares += dataArray[i] * dataArray[i];
                    }
                    let rms = Math.sqrt(sumSquares / dataArray.length);
                    let db = rms > 0 ? 20 * Math.log10(rms) : -100;
                    
                    if (db <= -55 && audioDbData.length > 0) {
                        db = audioDbData[audioDbData.length - 1];
                    }

                    audioDbData.shift();     
                    audioDbData.push(db);    
                    chartAudio.update();
                }, 20);

            } else {
                chartWrapper.style.display = "none";
                speakerGain.gain.value = 0; 
                
                if (audioChartIntervalId) {
                    clearInterval(audioChartIntervalId);
                    audioChartIntervalId = null;
                }
                checkAudioStop();
            }
        });

        document.getElementById('audioVolume').addEventListener('input', (e) => {
            if (speakerGain) speakerGain.gain.value = e.target.value;
        });


        // ==========================================
        // 畫面與資料混合錄製 (含音訊)
        // ==========================================
        const recordBtn = document.getElementById("recordBtn");
        const recordTimer = document.getElementById("recordTimer");
        const btnText = document.getElementById("btnText");
        
        const recCam = document.getElementById("recCam");
        const recChart = document.getElementById("recChart");
        const recAudio = document.getElementById("recAudio"); 
        
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

        recordBtn.addEventListener("click", async () => {
            if (!isRecording) {
                await startRecording();
            } else {
                stopRecording();
            }
        });

        async function startRecording() {
            const doCam = recCam.checked;
            const doChart = recChart.checked;
            const doAudio = recAudio.checked;

            if (!doCam && !doChart && !doAudio) {
                alert("請至少勾選一項要錄製的內容 (影像、數據圖 或 音訊)！");
                return;
            }

            if (doCam && (!camImg.complete || camImg.naturalWidth === 0)) {
                alert("影像尚未載入完成，請稍後再試！");
                return;
            }

            if (doAudio) {
                await initAudioSystem();
                speakerGain.gain.value = document.getElementById('audioToggle').checked ? document.getElementById('audioVolume').value : 0;
                ensureAudioStreaming();
            }

            let camW = 0, camH = 0;
            let chartW = 0, chartTotalH = 0;
            let chartBoxes = []; 
            const PADDING = 20;

            if (doCam) { camW = camImg.naturalWidth; camH = camImg.naturalHeight; }
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
            let totalH = Math.max(10, maxContentH + PADDING * 2);
            
            if (!doCam && !doChart) { totalW = 400; totalH = 300; }

            hiddenCanvas.width = totalW;
            hiddenCanvas.height = totalH;

            let camY = PADDING, chartStartY = PADDING;
            if (doCam && doChart) {
                if (camH < chartTotalH) camY = PADDING + (chartTotalH - camH) / 2;
                else chartStartY = PADDING + (camH - chartTotalH) / 2; 
            }

            recCam.disabled = true; recChart.disabled = true; recAudio.disabled = true;

            if (doCam || doChart) {
                recordIntervalId = setInterval(() => {
                    hiddenCtx.fillStyle = '#0f172a';
                    hiddenCtx.fillRect(0, 0, hiddenCanvas.width, hiddenCanvas.height);

                    let startX = PADDING;
                    if (doCam) {
                        if (camImg.naturalWidth > 0) hiddenCtx.drawImage(camImg, startX, camY, camW, camH);
                        startX += camW + PADDING;
                    }
                    if (doChart) {
                        let currentY = chartStartY;
                        for (let i = 0; i < chartCanvases.length; i++) {
                            let box = chartBoxes[i];
                            hiddenCtx.drawImage(chartCanvases[i], startX, currentY, box.w, box.h);
                            currentY += box.h; 
                        }
                    }
                }, 1000 / 30);
            }

            let combinedTracks = [];
            if (doCam || doChart) {
                const canvasStream = hiddenCanvas.captureStream(30);
                combinedTracks = [...canvasStream.getTracks()];
            }
            if (doAudio && audioDest) {
                combinedTracks = [...combinedTracks, ...audioDest.stream.getAudioTracks()];
            }
            const finalStream = new MediaStream(combinedTracks);

            const targetBitrate = 80000000; 
            const typesToTry = [
                'video/mp4;codecs=h264',   
                'video/mp4;codecs=avc1',
                'video/webm;codecs=h264',
                'video/webm;codecs=avc1',
                'video/webm;codecs=vp9',   
                'video/webm'
            ];

            let selectedMimeType = '';
            for (let type of typesToTry) {
                if (MediaRecorder.isTypeSupported(type)) {
                    selectedMimeType = type;
                    break;
                }
            }

            let options = { mimeType: selectedMimeType };
            if (doCam || doChart) options.videoBitsPerSecond = targetBitrate;

            try {
                mediaRecorder = new MediaRecorder(finalStream, options);
            } catch (e) {
                mediaRecorder = new MediaRecorder(finalStream);
            }
            
            mediaRecorder.actualMimeType = selectedMimeType;

            recordedChunks = [];
            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) recordedChunks.push(e.data);
            };

            mediaRecorder.onstop = () => {
                const mime = mediaRecorder.actualMimeType || 'video/webm';
                const ext = mime.includes('mp4') ? 'mp4' : 'webm';
                
                const blob = new Blob(recordedChunks, { type: mime });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                
                const dateStr = new Date().toISOString().replace(/[:T]/g, '-').slice(0, 19);
                a.download = `Record_${dateStr}.${ext}`;
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
            if (recordIntervalId) clearInterval(recordIntervalId);
            clearInterval(timerIntervalId);
            isRecording = false;
            
            recordBtn.classList.remove("recording");
            btnText.innerText = "錄影";
            recCam.disabled = false;
            recChart.disabled = false;
            recAudio.disabled = false;

            checkAudioStop(); 
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
    
    # [新增] 替換畫質變數
    html = html.replace("DEFAULT_QUALITY", str(DEFAULT_IMAGE_QUALITY))
    html = html.replace("MIN_QUALITY", str(MIN_IMAGE_QUALITY))
    html = html.replace("SLIDER_MAX_QUALITY", str(SLIDER_MAX_IMAGE_QUALITY))
    html = html.replace("MAX_QUALITY", str(MAX_IMAGE_QUALITY))
    
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
# ADXL API 
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
            "t": t_arr, "ax": ax_arr.tolist(), "ay": ay_arr.tolist(), 
            "az": az_arr.tolist(), "vector": vec_arr.tolist(), "server_id": SERVER_RUN_ID
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
            "t": t_out, "ax": ax_out.tolist(), "ay": ay_out.tolist(), 
            "az": az_out.tolist(), "vector": vec_out.tolist(), "server_id": SERVER_RUN_ID
        })

# --------------------------------------------------
# MJPEG Camera Stream
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
                
                if time_since_last >= interval_sec:
                    if latest_jpeg is not None:
                        yield (b"--frame\r\n" b"Content-Type:image/jpeg\r\n\r\n" + latest_jpeg + b"\r\n")
                    last_send_time = time.time()
                    continue 
                
                sleep_time = interval_sec - (time.time() - last_send_time)
                if sleep_time > 0:
                    time.sleep(min(sleep_time, 0.05))
                    
        except GeneratorExit:
            pass 
        except Exception:
            pass

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

# ==================================================
# 音訊 HTTP 即時串流 (Binary PCM)
# ==================================================
@app.route("/audio_raw")
def audio_raw():
    # [修改] 將 maxsize 從 100 降到 5 (約 300ms 的極小緩衝)，避免延遲堆積
    q = queue.Queue(maxsize=5) 
    with audio_lock:
        audio_subscribers.append(q)

    def generate():
        try:
            while True:
                yield q.get()
        except GeneratorExit:
            pass
        finally:
            with audio_lock:
                if q in audio_subscribers:
                    audio_subscribers.remove(q)

    return Response(generate(), mimetype="application/octet-stream")


# ==================================================
# Main
# ==================================================
if __name__ == "__main__":
    threading.Thread(target=adxl_receiver, daemon=True).start()
    threading.Thread(target=camera_receiver, daemon=True).start()
    threading.Thread(target=audio_receiver, daemon=True).start() 
    threading.Thread(target=client_monitor_thread, daemon=True).start()

    print(f"""
======================================
 ADXL355 + Camera + Audio Web Monitor
 Open: http://0.0.0.0:6969
 
 Server Started! Waiting for clients...
======================================
""")

    from waitress import serve
    serve(app, host="0.0.0.0", port=6969, threads=8)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import RPi.GPIO as GPIO
import pigpio, time, signal, sys, os
from threading import Thread

# ====== GPIO 設定 ======
BUTTON_PIN = 26  # 關機按鍵
LED_PIN = 16     # 提示燈
FAN_PIN = 12     # 風扇控制

# ====== 風扇 PWM 參數 ======
FREQ_HZ = 50       # 若風扇有高頻電流聲，建議改為 25000 (25kHz)
UPDATE_SEC = 5     # 每 5 秒更新一次

# ====== 溫度控制設定 ======
TEMP_START = 65.0  # 啟動風扇的溫度 (°C)
TEMP_STOP = 55.0   # 關閉風扇的溫度 (°C)
TEMP_MAX = 100.0   # 風扇滿轉的溫度 (°C)
MIN_DUTY = 50.0    # 剛啟動與降溫區間維持的基礎轉速 (%)

# 初始化 pigpio
pi = pigpio.pi()
if not pi.connected:
    print("pigpio daemon 未連線，請先啟動 pigpiod")
    sys.exit(1)

# ====== CPU 溫度相關函式 ======
fan_is_running = False  # 用來記錄目前風扇是否為「運轉狀態」

def get_cpu_temp_c():
    with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
        milli = int(f.read().strip())
    return milli / 1000.0

def temp_to_duty(temp_c):
    global fan_is_running
    
    # 1. 判斷是否需要切換風扇狀態
    if temp_c >= TEMP_START:
        fan_is_running = True
    elif temp_c <= TEMP_STOP:
        fan_is_running = False
        
    # 2. 如果風扇是停止狀態，直接回傳 0
    if not fan_is_running:
        return 0.0
        
    # 3. 如果風扇是運轉狀態，計算對應的轉速
    if temp_c <= TEMP_START:
        # 當溫度介於 TEMP_STOP (65) ~ TEMP_START (75) 之間，維持最低轉速
        duty = MIN_DUTY
    elif temp_c < TEMP_MAX:
        # 當溫度大於 TEMP_START (75)，開始線性加速
        duty = MIN_DUTY + (temp_c - TEMP_START) * ((100.0 - MIN_DUTY) / (TEMP_MAX - TEMP_START))
    else:
        duty = 100.0
        
    return max(0.0, min(100.0, duty))

def set_pwm_percent(pct):
    duty = int(pct / 100.0 * 1_000_000)
    pi.hardware_PWM(FAN_PIN, FREQ_HZ, duty)

# ====== 風扇控制執行緒 ======
def fan_control_loop():
    try:
        set_pwm_percent(75.0)  # 冷啟動先給 75% 確保馬達有足夠推力啟動
        time.sleep(7)          # 維持 5 秒
        while True:
            t = get_cpu_temp_c()
            duty = temp_to_duty(t)
            set_pwm_percent(duty)
            
            # 在終端機輸出目前溫度、轉速與運轉狀態
            status = "運轉中" if fan_is_running else "已停止"
            print(f"CPU 溫度: {t:.1f} °C | 風扇轉速: {duty:.1f} % [{status}]")   
            time.sleep(UPDATE_SEC)
    except Exception as e:
        print("風扇錯誤：", e)
        cleanup()

# ====== LED 與關機按鍵 ======
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(LED_PIN, GPIO.OUT)

GPIO.output(LED_PIN, GPIO.HIGH)  # 開機亮燈

press_time = None
blinking = False

# ====== 清理函式 ======
def cleanup(*_):
    print("清理 GPIO 和 PWM...")
    set_pwm_percent(0)  # 先停掉風扇
    GPIO.output(LED_PIN, GPIO.LOW)  # 確保 LED 熄滅
    pi.stop()
    GPIO.cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

# ====== 啟動風扇執行緒 ======
fan_thread = Thread(target=fan_control_loop, daemon=True)
fan_thread.start()

# ====== 主迴圈：處理按鈕與 LED ======
try:
    while True:
        if GPIO.input(BUTTON_PIN) == GPIO.LOW:  # 按下
            if press_time is None:
                press_time = time.time()
                blinking = True
            elif time.time() - press_time >= 3:
                print("長按3秒，準備關機...")
                os.system("sudo systemctl poweroff")
                cleanup()
        else:
            press_time = None
            blinking = False
            GPIO.output(LED_PIN, GPIO.HIGH)

        if blinking:
            GPIO.output(LED_PIN, not GPIO.input(LED_PIN))

        time.sleep(0.25 if blinking else 0.1)

except Exception as e:
    print("主程式錯誤：", e)
    cleanup()

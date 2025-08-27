import RPi.GPIO as GPIO
import time
import os

BUTTON_PIN = 26  # 設定接的腳位

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

press_time = None

try:
    while True:
        if GPIO.input(BUTTON_PIN) == GPIO.LOW:  # 按下
            if press_time is None:
                press_time = time.time()
            elif time.time() - press_time >= 5:  # 長按 5 秒
                print("長按5秒，準備關機...")
                os.system("sudo shutdown -h now")
                break
        else:
            press_time = None  # 放開就重置計時

        time.sleep(0.1)

except KeyboardInterrupt:
    pass

finally:
    GPIO.cleanup()

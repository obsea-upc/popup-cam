import RPi.GPIO as GPIO
import traceback
from datetime import datetime
import time

log_file = 'log_file.txt'

def log_error():
    with open(log_file, "a") as f:
        f.write(f"\nError occurred at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(traceback.format_exc())
        f.write("\n" + "-"*60 + "\n")

GPIO.setmode(GPIO.BCM)
GPIO.setup(15, GPIO.OUT)

try:
    with open(log_file, "a") as f:
        f.write(f"\nUV Lights ON at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("\n" + "-"*60 + "\n")
    GPIO.output(15, GPIO.HIGH)
    print("GPIO 15 ON")
    time.sleep(60)
    GPIO.output(15, GPIO.LOW)
    print("GPIO 15 OFF")
    with open(log_file, "a") as f:
        f.write(f"\nUV Lights OFF at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("\n" + "-"*60 + "\n")
except Exception:
    log_error()
finally:
    GPIO.cleanup()
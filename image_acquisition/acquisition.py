from ultralytics import YOLO
import subprocess
import time
import json
import os
import signal
import sys
import cv2
import RPi.GPIO as GPIO
import threading
from datetime import datetime 
import traceback

global pin_pwm
global ethernet
global wifi
pin_pwm = 18
folder = "/home/SN001/image_acquisition"
log_file = "/home/SN001/image_acquisition/error_log.txt"
srv_addr = "192.168.1.100"

# - - - Log Function - - -
def log_error():
    with open(log_file, "a") as f:
        f.write(f"\nError occurred at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(traceback.format_exc())
        f.write("\n" + "-"*60 + "\n")

def create_timestamped_directories(base_folder):
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    day = now.strftime("%d")
    path = os.path.join(base_folder, 'static', year, month, day)
    os.makedirs(path, exist_ok=True)
    return path

def take_picture(focus_t,width,height,filename):
    current_hour = datetime.now().hour
    print(current_hour)
    if 0 <= current_hour <= 6 or 17 <= current_hour <= 23:
        awb_gains = "2.0,2.0"
        exp = "sport"
    else:                                       # Horas de dia
        awb_gains = "7.6,1.6"
        exp = "normal"
    commande = (f'sudo libcamera-still -t 15 --width {width} --height {height} --autofocus-mode manual --lens-position 11 --exposure {exp} --awbgains {awb_gains} -o {filename}.jpg')
    subprocess.run(commande, shell=True, capture_output=True, text=True)
    with open(log_file, 'a') as f:
            f.write(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Image taken with parameters: exposure mode [{exp}], awb gains [{awb_gains}]\n")
    print("Photo capture complete.")
    os.system(f"scp {filename}.jpg {srv_addr}:/opt/acquisition/pics/PopUp_Cam-SN001")
    print('Image successfully pushed to server')
    
def open_pwm(pin_pwm,frequency):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin_pwm, GPIO.OUT)
    pwm = GPIO.PWM(pin_pwm, frequency)
    avant = datetime.now()
    time.sleep(1) # delay for coverging of both threads (3 opt.)
    pwm.start(50)
    time.sleep(5) # flash duration (1 opt.)
    pwm.stop()
    apres = datetime.now()
    print(apres-avant)
    print("PWM control complete.")

# - - - Light Parameters - - -

def calculate_light(image_path):
    image = cv2.imread(image_path)
    image_grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    luminosite_moyenne = image_grayscale.mean()
    print('The average score of light in the picture is {:.2f}'.format(luminosite_moyenne))
    return luminosite_moyenne

def main_lights(config, absolute_path, width, height):
    focus_t = int(config['focus_t'])*1000
    print('aaa')
    print(absolute_path)
    commande = f"sudo libcamera-still -t 1 --width {width} --height {height} --autofocus-mode manual --lens-position 12 --awbgains 7.6,1.6 -o {absolute_path}/photo_before_flash.jpg"
    resultat = subprocess.run(commande, shell=True, capture_output=True, text=True)
    if os.path.exists(f"{absolute_path}/photo_before_flash.jpg") == True:
        print("The picture before flash has been taken")
        image_path = f"{absolute_path}/photo_before_flash.jpg"
        light = calculate_light(image_path)
        score = "undefined"
        with open(folder + '/config_files/light_config.json') as json_file:
            light_config = json.load(json_file)
        for category in light_config["categories"]:
            lower, upper = category["range"]
            if (lower == "inf" or light >= lower) and (upper == "inf" or light < upper):
                score = category["label"]
                break
        print(f"It's {score} right there")
        freq_min = 50   # Hz
        freq_max = 350  # Hz # <<<Changed from 450 to 350>>>
        score_min = 0   # 0%
        score_max = 150
        score_perc = (light/score_max)*100
        frequency = ((light - score_min) / (score_max - score_min)) * (freq_max - freq_min) + freq_min
        print('The frequency of the lights is {:.0f}'.format(frequency),"Hz")
        print('That corresponds to {:.0f}'.format(score_perc),"% of brightness")
        timestamp = time.strftime('%Y%m%d-%H%M%S')
        filename = f"{timestamp}-PopUp_Cam_001"
        photo_thread = threading.Thread(target=take_picture, args=(focus_t,width,height,f'{absolute_path}/'+filename))
        pwm_thread = threading.Thread(target=open_pwm, args=(pin_pwm,frequency))
        photo_thread.start()
        pwm_thread.start()
        photo_thread.join()
        pwm_thread.join()
        GPIO.cleanup()
        if os.path.exists(absolute_path+'/'+filename+'.jpg'):
            calculate_light(absolute_path+'/'+filename+'.jpg')
        else:
            print("Something went wrong with the image taking")
        return filename, frequency 
    else:
        print("Something went wrong with the image taking.")
# - - -
# - - - Main Code Setup - - -
def yolo_run(absolute_path, file_path, time_stamp):
    print(absolute_path + '/' + file_path)
    print('Starting inference with YOLOv8')
    results = model(str(absolute_path + '/' + file_path + '.jpg'), stream=True, verbose=False)
    detections = []
    for result in results:
        boxes = result.boxes
        if boxes:
            for box in boxes:
                cls_id = int(box.cls[0])
                class_name = model.names[cls_id]
                confidence = float(box.conf[0])
                x_min, y_min, x_max, y_max = map(float, box.xyxy[0])
                detections.append({"taxa": class_name, "confidence": round(confidence, 3), "bounding_box_xyxy": [round(x_min, 3), round(y_min, 3), round(x_max, 3), round(y_max, 3)]})
        os.makedirs(f'{absolute_path}/AI_Results/', exist_ok=True)
        filename = f'{absolute_path}/AI_Results/' + file_path + '.jpg'
        result.save(filename)
    ai_results = {"phenomenonTime": time_stamp,
        "resultTime": time_stamp,
        "result": detections}
    json_object_counts = json.dumps(ai_results, indent=1)
    json_filename = f"{absolute_path}/AI_Results/{file_path}.json"
    with open(json_filename, 'w') as json_file:
        json_file.write(json_object_counts)
    print(json_object_counts)
    print('End of the inference')
    return json_filename, filename

def main():
    try:
        

        time_now = datetime.now()
        timestamp_json = time_now.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        with open(folder + '/config_files/config.json') as json_file:
            config = json.load(json_file)
        timestamped_path = create_timestamped_directories(folder)
        print(f"Files will be saved in: {timestamped_path}")
        global model
        if config['size'] == 'nano':
            model = YOLO(folder + '/Biotope_nano.pt')
        elif config['size'] == 'large':
            model = YOLO(folder + '/Biotope_large.pt')
        else:
            print('No model available, check form responses')
        period = int(config['period'])
        return_second_photo, lightning = main_lights(config, timestamped_path, int(config['width']), int(config['height']))
        if config['inferencia'] == "Yes":
            yolo_run(timestamped_path,return_second_photo,timestamp_json)
        print(f"Waiting until the next session")
        with open(log_file, 'a') as f:
            f.write(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Waiting until the next session\n")
    except Exception:
        log_error()
 
# - - -
def sigint_handler(sig, frame):
    os.kill(os.getpid(), signal.SIGKILL)  # Finish all processes
    sys.exit(1)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigint_handler)
    try:
        main()
    except KeyboardInterrupt:
        sigint_handler(signal.SIGINT, None)

import RPi.GPIO as GPIO
import time

# Configura la numeración BCM de los pines
GPIO.setmode(GPIO.BCM)
GPIO.setup(15, GPIO.OUT)

try:
    # Activa el GPIO 10
    GPIO.output(15, GPIO.HIGH)
    print("GPIO 10 activado")
    time.sleep(60)  # Espera 1 minuto
    # Desactiva el GPIO 10
    GPIO.output(15, GPIO.LOW)
    print("GPIO 10 desactivado")
finally:
    GPIO.cleanup()

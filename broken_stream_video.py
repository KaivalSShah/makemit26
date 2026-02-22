# https://pip-assets.raspberrypi.com/categories/652-raspberry-pi-camera-module-2/documents/RP-008156-DS-2-picamera2-manual.pdf?disposition=inline
# sudo apt install -y python3-picamera2
# sudo aptupdate
# sudo apt full-upgrade
# sudo apt-get install libcap-dev
# 
# /boot/firmware/config.txt
# camera_auto_detect = 0
# dtoverlay=ov9281,cam0

from picamera2 import Picamera2, Preview
import time
picam2 = Picamera2()
camera_config = picam2.create_preview_configuration()
picam2.configure(camera_config)
# picam2.start_preview(Preview.DRM)
picam2.start()
time.sleep(2)
picam2.capture_file("test.jpg")

# PWM
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BOARD)		#set pin numbering system
GPIO.setup(ledpin,GPIO.OUT)
pi_pwm = GPIO.PWM(ledpin,1000)
pi_pwm.start(0)




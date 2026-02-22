from picamera2 import Picamera2
import cv2
import time

picam2 = Picamera2()

still_config = picam2.create_still_configuration(
    main={"format": "YUV420", "size": (1280, 800)},
    raw=None
)

picam2.configure(still_config)
picam2.start()
# time.sleep(1)  # let exposure settle

frame = picam2.capture_array("main")
# frame = picam2.switch_mode_and_capture_array(still_config, "main")

gray = frame[:800, :]  # Y plane
cv2.imwrite("image2.png", gray)
print("Saved image.png")

picam2.stop()
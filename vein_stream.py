from picamera2 import Picamera2
import numpy as np
import cv2
import io
import threading
import time
from http.server import SimpleHTTPRequestHandler, HTTPServer

WIDTH, HEIGHT = 1280, 800


class StreamingOutput:
    def __init__(self):
        self.frame = None
        self.condition = threading.Condition()

    def update(self, jpeg_bytes):
        with self.condition:
            self.frame = jpeg_bytes
            self.condition.notify_all()


def detect_veins(gray):
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    blurred = cv2.GaussianBlur(enhanced, (5, 5), 0).astype(np.float64)

    sigma = 2.0
    ksize = 5
    Ixx = cv2.Sobel(blurred, cv2.CV_64F, 2, 0, ksize=ksize) * sigma ** 2
    Iyy = cv2.Sobel(blurred, cv2.CV_64F, 0, 2, ksize=ksize) * sigma ** 2
    Ixy = cv2.Sobel(blurred, cv2.CV_64F, 1, 1, ksize=ksize) * sigma ** 2

    tmp = np.sqrt((Ixx - Iyy) ** 2 + 4 * Ixy ** 2)
    lambda1 = 0.5 * (Ixx + Iyy + tmp)
    lambda2 = 0.5 * (Ixx + Iyy - tmp)

    ridges = np.where(np.abs(lambda1) > np.abs(lambda2), lambda1, lambda2)
    ridges = np.clip(ridges, 0, None)

    if ridges.max() > 0:
        ridges = (ridges / ridges.max() * 255).astype(np.uint8)
    else:
        ridges = np.zeros_like(gray)

    _, vein_mask = cv2.threshold(ridges, 30, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    vein_mask = cv2.morphologyEx(vein_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    vein_mask = cv2.morphologyEx(vein_mask, cv2.MORPH_OPEN, kernel, iterations=1)

    return ridges, vein_mask


raw_out = StreamingOutput()
veins_out = StreamingOutput()
overlay_out = StreamingOutput()


PAGE = f"""<!DOCTYPE html>
<html>
<head>
    <title>OV9281 Vein Detection</title>
    <style>
        body {{ background: #111; color: #eee; font-family: sans-serif; margin: 20px; }}
        h1 {{ color: #0f0; }}
        .streams {{ display: flex; flex-wrap: wrap; gap: 20px; }}
        .stream {{ text-align: center; }}
        .stream img {{ border: 1px solid #333; max-width: 640px; }}
        .stream h3 {{ margin-bottom: 8px; }}
    </style>
</head>
<body>
    <h1>OV9281 NIR Vein Detection</h1>
    <div class="streams">
        <div class="stream">
            <h3>Raw Camera</h3>
            <img src="/raw.mjpg" />
        </div>
        <div class="stream">
            <h3>Ridge Detection</h3>
            <img src="/veins.mjpg" />
        </div>
        <div class="stream">
            <h3>Overlay</h3>
            <img src="/overlay.mjpg" />
        </div>
    </div>
</body>
</html>"""

STREAMS = {
    "raw": raw_out,
    "veins": veins_out,
    "overlay": overlay_out,
}


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(PAGE.encode())
            return

        name = self.path.lstrip('/').removesuffix('.mjpg')
        stream = STREAMS.get(name)
        if stream is None:
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
        self.end_headers()
        try:
            while True:
                with stream.condition:
                    stream.condition.wait()
                    frame = stream.frame
                self.wfile.write(b'--FRAME\r\n')
                self.wfile.write(b'Content-Type: image/jpeg\r\n')
                self.wfile.write(f'Content-Length: {len(frame)}\r\n\r\n'.encode())
                self.wfile.write(frame)
        except Exception:
            pass

    def log_message(self, format, *args):
        pass


def processing_loop(picam2):
    while True:
        buf = picam2.capture_array("main")
        gray = buf[:HEIGHT, :].astype(np.uint8)

        _, raw_jpg = cv2.imencode('.jpg', gray)
        raw_out.update(raw_jpg.tobytes())

        ridges, vein_mask = detect_veins(gray)

        _, veins_jpg = cv2.imencode('.jpg', ridges)
        veins_out.update(veins_jpg.tobytes())

        color = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        color[vein_mask > 0] = (0, 255, 0)
        _, overlay_jpg = cv2.imencode('.jpg', color)
        overlay_out.update(overlay_jpg.tobytes())

        time.sleep(0.03)


picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"format": "YUV420", "size": (WIDTH, HEIGHT)},
    sensor={"bit_depth": 8}
)
picam2.configure(config)
picam2.start()

thread = threading.Thread(target=processing_loop, args=(picam2,), daemon=True)
thread.start()

server = HTTPServer(('0.0.0.0', 8000), Handler)
print("Vein detection streaming at http://0.0.0.0:8000")
print("  /          - Dashboard")
print("  /raw.mjpg  - Raw camera")
print("  /veins.mjpg - Ridge detection")
print("  /overlay.mjpg - Vein overlay")
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    picam2.stop()

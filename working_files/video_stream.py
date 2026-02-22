from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput
import io, os, time, threading
from http.server import SimpleHTTPRequestHandler, HTTPServer

PAGE = """
<html><body>
<img src="stream.mjpg" width="1280" height="800" /><br>
<button onclick="fetch('/capture',{method:'POST'}).then(r=>r.text()).then(t=>alert(t))">Capture Image</button>
</body></html>
"""

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = threading.Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

SAVE_DIR = os.path.dirname(os.path.abspath(__file__))

class StreamingHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/capture':
            try:
                with output.condition:
                    output.condition.wait()
                    frame = output.frame

                save_path = os.path.join(SAVE_DIR, f"capture_{int(time.time())}.jpg")
                with open(save_path, 'wb') as f:
                    f.write(frame)

                msg = f"Saved {save_path}"
                self.send_response(200)
            except Exception as e:
                msg = f"Error: {e}"
                self.send_response(500)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(msg.encode())

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(PAGE.encode())
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
            except Exception:
                pass

output = StreamingOutput()
picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"format": "YUV420", "size": (1280, 800)},
    sensor={"bit_depth": 8}
)
picam2.configure(config)
picam2.start_recording(MJPEGEncoder(), FileOutput(output))

server = HTTPServer(('0.0.0.0', 8000), StreamingHandler)
print("Streaming at http://<your-pi-ip>:8000")
try:
    server.serve_forever()
finally:
    picam2.stop_recording()
from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput
from socketserver import ThreadingMixIn
import io, threading, time
from http.server import SimpleHTTPRequestHandler, HTTPServer

PAGE = """
<html><body style="text-align:center; background:#222; color:#fff; font-family:sans-serif;">
<h2>Pi Camera Stream</h2>
<img src="stream.mjpg" width="1280" height="800" /><br><br>
<button onclick="capture()" style="padding:15px 40px; font-size:20px; cursor:pointer;">
    Capture Photo
</button>
<p id="status"></p>
<script>
async function capture() {
    document.getElementById('status').innerText = 'Capturing...';
    try {
        const res = await fetch('/capture');
        const data = await res.json();
        document.getElementById('status').innerText = data.message;
    } catch(e) {
        document.getElementById('status').innerText = 'Error: ' + e;
    }
}
</script>
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

class StreamingHandler(SimpleHTTPRequestHandler):
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
                    self.wfile.write(b'Content-Type: image/jpeg\r\n')
                    self.wfile.write(f'Content-Length: {len(frame)}\r\n'.encode())
                    self.wfile.write(b'\r\n')
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception:
                pass
        elif self.path == '/capture':
            print("Capture requested")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            try:
                # still_config = picam2.create_still_configuration(
                #     main={"format": "YUV420", "size": (1280, 800)},
                #     raw=None
                # )
                # frame = picam2.switch_mode_and_capture_array(still_config, "main", delay=1)
                # gray = frame[:800, :]  # Y plane

                # timestamp = time.strftime("%Y%m%d_%H%M%S")
                # filename = f"capture_{timestamp}.png"
                # cv2.imwrite(filename, gray)
                # print(f"Saved {filename}")
                # msg = f"Saved {filename}"
                with output.condition:
                    output.condition.wait()
                    frame = output.frame


                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"capture_{timestamp}.jpg"
                with open(filename, 'wb') as f:
                    f.write(frame)
                msg = f"Saved {filename}"
                print(msg)
            except Exception as e:
                msg = f"Error: {e}"
                print(msg)
            self.wfile.write(f'{{"message": "{msg}"}}'.encode())
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        print(args[0])

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

output = StreamingOutput()
picam2 = Picamera2()
config = picam2.create_video_configuration(
    sensor={'output_size': (1280, 800), "bit_depth": 10}
)
picam2.configure(config)
print(picam2.camera_configuration())

picam2.start_recording(MJPEGEncoder(), FileOutput(output))

server = ThreadedHTTPServer(('0.0.0.0', 8000), StreamingHandler)
print("Streaming at http://0.0.0.0:8000")
try:
    server.serve_forever()
finally:
    picam2.stop_recording()
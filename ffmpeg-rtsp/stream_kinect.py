#!/usr/bin/env python3
import freenect
import cv2
import subprocess
import numpy as np
import os
import socket
import time

# RTSP streaming URL
DEFAULT_RTSP_URL = "rtsp://rtsp-server:8554/kinect"
rtsp_target = os.environ.get("RTSP_TARGET", DEFAULT_RTSP_URL)

# Extract host and port for connection check
def parse_rtsp_url(url):
    url = url.replace("rtsp://", "")
    host_port, _ = url.split("/", 1)
    host, port = host_port.split(":")
    return host, int(port)

host, port = parse_rtsp_url(rtsp_target)

# Wait for RTSP server to be ready
print(f"⏳ Waiting for RTSP server at {host}:{port}...")
while True:
    try:
        with socket.create_connection((host, port), timeout=1):
            print(f"✅ RTSP server is up at {host}:{port}")
            break
    except (ConnectionRefusedError, socket.timeout):
        time.sleep(1)

# FFmpeg command
ffmpeg_cmd = [
    "ffmpeg",
    "-thread_queue_size", "512",
    "-f", "rawvideo",
    "-pix_fmt", "bgr24",
    "-s:v", "640x480",
    "-r", "15",
    "-i", "-",
    # timing / stability
    "-use_wallclock_as_timestamps", "1",
    "-fflags", "+genpts",
    # encode
    "-c:v", "libx264",
    "-preset", "ultrafast",
    "-tune", "zerolatency",
    "-profile:v", "baseline",
    "-level", "3.1",
    "-pix_fmt", "yuv420p",
    "-g", "30",
    "-x264-params", "keyint=30:min-keyint=30:scenecut=0:repeat-headers=1",
    "-b:v", "1200k",
    "-maxrate", "1200k",
    "-bufsize", "2400k",
    # RTSP transport
    "-f", "rtsp",
    "-rtsp_transport", "tcp",
    rtsp_target
]

# Function to start FFmpeg with retry
def start_ffmpeg(max_retries=5, delay=2):
    retries = 0
    while True:
        try:
            proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
            print(f"🟢 Kinect RGB streamer started. Serving RTSP at {rtsp_target}")
            return proc
        except Exception as e:
            retries += 1
            print(f"⚠️ FFmpeg failed to start: {e}")
            if retries >= max_retries:
                raise RuntimeError("FFmpeg failed too many times. Exiting.")
            print(f"🔁 Retrying in {delay}s...")
            time.sleep(delay)

proc = start_ffmpeg()

# Main loop to capture and send frames
try:
    while True:
        frame = None
        try:
            frame_tuple = freenect.sync_get_video()
            if frame_tuple is None:
                continue
            frame, _ = frame_tuple
        except Exception:
            continue
        if frame is None:
            continue
        bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        try:
            proc.stdin.write(bgr.tobytes())
        except BrokenPipeError:
            print("⚠️ FFmpeg pipe broken. Restarting FFmpeg...")
            try:
                proc.stdin.close()
            except Exception:
                pass
            proc.wait()
            proc = start_ffmpeg()
        time.sleep(1/15)   # keep source at ~15 fps
except KeyboardInterrupt:
    print("🛑 Stopping streamer...")
finally:
    proc.stdin.close()
    proc.wait()

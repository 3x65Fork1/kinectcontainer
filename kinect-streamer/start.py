#!/usr/bin/env python3
import os
import time
import subprocess
import freenect
import numpy as np
from datetime import datetime

# === Config ===
PORT = int(os.getenv("RTSP_PORT", "8554"))
STREAM_NAME = os.getenv("STREAM_NAME", "stream")
DEPTH_THRESHOLD = int(os.getenv("DEPTH_THRESHOLD", "1200"))  # in mm
RECORDINGS_DIR = os.getenv("RECORDINGS_DIR", "/camera-ui/recordings")
MIN_EVENT_DURATION = float(os.getenv("MIN_EVENT_DURATION", "5"))  # seconds

os.makedirs(RECORDINGS_DIR, exist_ok=True)

def start_ffmpeg_stream():
    """Start RTSP stream for live feed (RGB) with 180° flip."""
    print("📡 Starting RTSP stream...")
    return subprocess.Popen([
        "ffmpeg",
        "-f", "video4linux2", "-i", "/dev/video0",
        "-vf", "transpose=2,transpose=2",  # 180° flip
        "-vcodec", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
        "-f", "rtsp", f"rtsp://0.0.0.0:{PORT}/{STREAM_NAME}"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def start_recording():
    """Start recording the RGB feed to a file."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(RECORDINGS_DIR, f"record_{ts}.mp4")
    print(f"🎥 Starting recording → {filename}")
    proc = subprocess.Popen([
        "ffmpeg",
        "-f", "video4linux2", "-i", "/dev/video0",
        "-vf", "transpose=2,transpose=2",  # 180° flip
        "-vcodec", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
        filename
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc, filename

def stop_recording(proc):
    """Stop the FFmpeg recording process."""
    print("🛑 Stopping recording...")
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()

def main():
    print("🤖 Kinect streamer with depth-triggered recording starting...")
    rtsp_proc = start_ffmpeg_stream()
    recording_proc = None
    last_trigger_time = 0
    triggered = False

    try:
        while True:
            depth_frame, _ = freenect.sync_get_depth()
            if depth_frame is None:
                print("⚠️ No depth frame received!")
                time.sleep(1)
                continue

            min_depth = np.min(depth_frame)
            avg_depth = np.mean(depth_frame)
            print(f"Depth min: {min_depth} mm, avg: {avg_depth:.1f} mm")

            # Trigger recording if min depth below threshold
            if min_depth < DEPTH_THRESHOLD and not triggered:
                triggered = True
                last_trigger_time = time.time()
                recording_proc, filename = start_recording()

            # Stop recording if depth rises above threshold
            elif triggered and min_depth > DEPTH_THRESHOLD:
                if time.time() - last_trigger_time > MIN_EVENT_DURATION:
                    triggered = False
                    if recording_proc:
                        stop_recording(recording_proc)
                        recording_proc = None

            time.sleep(0.2)

    finally:
        if recording_proc:
            stop_recording(recording_proc)
        rtsp_proc.terminate()
        print("✅ Kinect streamer stopped.")

if __name__ == "__main__":
    main()

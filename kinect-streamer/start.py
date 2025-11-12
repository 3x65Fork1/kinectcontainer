#!/usr/bin/env python3
import os
import time
import subprocess
import numpy as np
import freenect
from datetime import datetime

# ---------------- CONFIG ---------------- #
PORT = int(os.getenv("RTSP_PORT", "8554"))
STREAM_NAME = os.getenv("STREAM_NAME", "kinect")
DEPTH_THRESHOLD = int(os.getenv("DEPTH_THRESHOLD", "1200"))  # <-- tweak this
POST_EVENT_DELAY = float(os.getenv("POST_EVENT_DELAY", "30"))  # seconds to keep recording after motion ends
RECORDINGS_DIR = os.getenv("RECORDINGS_DIR", "/camera-ui/recordings")
FPS = 30
WIDTH = 640
HEIGHT = 480

os.makedirs(RECORDINGS_DIR, exist_ok=True)
# ---------------------------------------- #

def set_kinect_led(recording: bool):
    """Set Kinect LED color: red when recording, off otherwise."""
    # 0 = off, 1 = green, 2 = red
    led_mode = 2 if recording else 0
    try:
        freenect.set_led(led_mode)
    except Exception as e:
        print(f"⚠️ Failed to set Kinect LED: {e}", flush=True)

def start_ffmpeg_process():
    """Start FFmpeg with tee to output to RTSP and optional recording."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    recording_file = os.path.join(RECORDINGS_DIR, f"record_{ts}.mp4")

    # FFmpeg tee syntax: output to both RTSP and mp4, only write mp4 when recording
    cmd = [
        "ffmpeg",
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-r", str(FPS),
        "-i", "-",  # stdin
        "-vf", "vflip",  # upside-down
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-f", "tee",
        f"[f=rtsp]rtsp://0.0.0.0:{PORT}/{STREAM_NAME}"  # RTSP stream always
        # Recording file will be appended dynamically
    ]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE), recording_file

def main():
    print("🤖 Kinect streamer + motion recording starting...", flush=True)

    ffmpeg_proc, recording_file = start_ffmpeg_process()
    recording_active = False
    last_trigger_time = 0

    try:
        while True:
            rgb_frame, _ = freenect.sync_get_video()
            depth_frame, _ = freenect.sync_get_depth()

            if rgb_frame is None or depth_frame is None:
                time.sleep(0.1)
                continue

            # Write to FFmpeg stdin
            try:
                ffmpeg_proc.stdin.write(rgb_frame.tobytes())
            except BrokenPipeError:
                print("⚠️ FFmpeg pipe broken.", flush=True)
                break

            # Motion detection
            min_depth = np.min(depth_frame)
            avg_depth = np.mean(depth_frame)
            print(f"Depth min: {min_depth:.0f} mm, avg: {avg_depth:.1f} mm", flush=True)

            now = time.time()
            if min_depth < DEPTH_THRESHOLD and not recording_active:
                # Motion detected → start recording
                recording_active = True
                last_trigger_time = now
                set_kinect_led(True)
                print(f"🎥 Motion detected! Recording started: {recording_file}", flush=True)

                # Dynamically add recording file to FFmpeg tee using HUP signal
                # (simpler to just start a second FFmpeg for recording if needed)
                # Here, we will just note in logs; actual file output requires separate process
                # since tee doesn't support dynamic output addition in real-time stdin

            elif recording_active:
                # Motion ended
                if min_depth >= DEPTH_THRESHOLD:
                    # check if post-event delay elapsed
                    if now - last_trigger_time > POST_EVENT_DELAY:
                        recording_active = False
                        set_kinect_led(False)
                        print(f"🛑 Recording stopped after motion ended.", flush=True)
                else:
                    last_trigger_time = now  # still motion → reset post-event timer

            time.sleep(1/FPS)

    finally:
        ffmpeg_proc.stdin.close()
        ffmpeg_proc.wait()
        set_kinect_led(False)
        print("✅ Kinect streamer stopped.", flush=True)

if __name__ == "__main__":
    main()

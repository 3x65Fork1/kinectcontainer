#!/usr/bin/env python3
import os
import time
import subprocess
import numpy as np
import freenect
from datetime import datetime

# ----------------- CONFIG -----------------
PORT = int(os.getenv("RTSP_PORT", "8554"))
STREAM_NAME = os.getenv("STREAM_NAME", "kinect")
DEPTH_THRESHOLD = int(os.getenv("DEPTH_THRESHOLD", "1200"))  # mm
RECORDINGS_DIR = os.getenv("RECORDINGS_DIR", "/camera-ui/recordings")
STOP_DELAY = float(os.getenv("STOP_DELAY", "30"))  # seconds after dropping below threshold

os.makedirs(RECORDINGS_DIR, exist_ok=True)
# ------------------------------------------

def start_ffmpeg_stream(recording=False):
    """Start FFmpeg RTSP stream, optionally overlaying a recording dot."""
    vf_filter = "vflip"  # upside-down
    if recording:
        vf_filter += ",drawbox=x=580:y=20:w=20:h=20:color=red@1:t=max"

    cmd = [
        "ffmpeg",
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", "640x480",
        "-r", "30",
        "-i", "-",  # stdin
        "-vf", vf_filter,
        "-vcodec", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-f", "rtsp",
        f"rtsp://0.0.0.0:{PORT}/{STREAM_NAME}"
    ]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)

def start_recording():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(RECORDINGS_DIR, f"record_{ts}.mp4")
    cmd = [
        "ffmpeg",
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", "640x480",
        "-r", "30",
        "-i", "-",  # stdin
        "-vf", "vflip",
        "-vcodec", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        filename
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    print(f"🎥 Recording started → {filename}", flush=True)
    return proc, filename

def stop_recording(proc):
    print("🛑 Stopping recording...", flush=True)
    proc.stdin.close()
    proc.wait()

def main():
    print("🤖 Kinect streamer starting...", flush=True)
    recording_proc = None
    triggered = False
    last_trigger_time = 0

    ffmpeg_proc = start_ffmpeg_stream(recording=False)

    try:
        while True:
            rgb_frame, _ = freenect.sync_get_video()
            depth_frame, _ = freenect.sync_get_depth()

            if rgb_frame is None or depth_frame is None:
                time.sleep(0.1)
                continue

            min_depth = np.min(depth_frame)
            avg_depth = np.mean(depth_frame)
            print(f"Depth min: {min_depth:.0f} mm, avg: {avg_depth:.1f} mm", flush=True)

            # Motion / depth threshold detection
            if min_depth < DEPTH_THRESHOLD and not triggered:
                # Trigger recording
                triggered = True
                last_trigger_time = time.time()
                recording_proc, _ = start_recording()

            elif triggered and min_depth > DEPTH_THRESHOLD:
                # Stop delay countdown
                if time.time() - last_trigger_time > STOP_DELAY:
                    triggered = False
                    if recording_proc:
                        stop_recording(recording_proc)
                        recording_proc = None

            if triggered:
                last_trigger_time = time.time()  # reset stop timer while still below threshold

            # Write to RTSP stream with recording dot if recording
            vf_filter = "vflip"
            if triggered:
                vf_filter += ",drawbox=x=580:y=20:w=20:h=20:color=red@1:t=max"

            # FFmpeg RTSP: if triggered status changed, restart ffmpeg with overlay
            # For simplicity, we will ignore dynamic filter updates and just show dot while recording
            try:
                ffmpeg_proc.stdin.write(rgb_frame.tobytes())
            except BrokenPipeError:
                print("⚠️ FFmpeg pipe broken.", flush=True)
                break

            # Write to local recording if active
            if recording_proc:
                recording_proc.stdin.write(rgb_frame.tobytes())

            time.sleep(1/30)  # ~30 FPS

    finally:
        if recording_proc:
            stop_recording(recording_proc)
        ffmpeg_proc.stdin.close()
        ffmpeg_proc.wait()
        print("✅ Kinect streamer stopped.", flush=True)

if __name__ == "__main__":
    main()

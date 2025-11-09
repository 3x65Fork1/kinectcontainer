import cv2
import numpy as np
import requests
import os
import time

RTSP_STREAM = os.getenv("RTSP_STREAM", "rtsp://kinect-streamer:8554/stream")
NVR_API_URL = os.getenv("NVR_API_URL")

def trigger_nvr(event: str):
    if not NVR_API_URL:
        print("⚠️ NVR_API_URL not set.")
        return
    try:
        print(f"Triggering NVR: {event}")
        requests.post(NVR_API_URL, json={"event": event})
    except Exception as e:
        print("Error contacting NVR:", e)

def main():
    cap = cv2.VideoCapture(RTSP_STREAM)
    if not cap.isOpened():
        print("Failed to open RTSP stream.")
        return

    prev_frame = None
    motion_detected = False

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(1)
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if prev_frame is None:
            prev_frame = gray
            continue

        diff = cv2.absdiff(prev_frame, gray)
        thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
        motion_area = np.sum(thresh) / 255

        if motion_area > 5000 and not motion_detected:
            motion_detected = True
            trigger_nvr("start_recording")

        elif motion_area < 2000 and motion_detected:
            motion_detected = False
            trigger_nvr("stop_recording")

        prev_frame = gray
        time.sleep(0.1)

if __name__ == "__main__":
    main()

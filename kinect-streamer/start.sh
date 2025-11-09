#!/bin/bash
set -e

STREAM_NAME="stream"
PORT="${RTSP_PORT:-8554}"

# Capture RGB with libfreenect and pipe to ffmpeg
# Flip video 180 degrees, encode as H.264, and serve via RTSP
freenect-glview &  # optional to wake device

# Start ffmpeg RTSP server
ffmpeg -f video4linux2 -i /dev/video0 \
  -vf "transpose=2,transpose=2" \  # 180° flip
  -vcodec libx264 -preset ultrafast -tune zerolatency \
  -f rtsp rtsp://rtsp-server:${PORT}/${STREAM_NAME}

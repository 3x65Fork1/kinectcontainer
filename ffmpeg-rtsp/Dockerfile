FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg libfreenect0.5 libfreenect-dev python3 python3-pip \
    v4l-utils usbutils && \
    pip3 install numpy opencv-python && \
    rm -rf /var/lib/apt/lists/*

# Install Python freenect bindings
RUN pip install --no-cache-dir freenect numpy opencv-python

WORKDIR /app
COPY stream_kinect.py .

RUN chmod +x stream_kinect.py

CMD ["python3", "stream_kinect.py"]

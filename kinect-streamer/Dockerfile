FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    build-essential cmake git pkg-config \
    libfreenect-dev ffmpeg v4l-utils \
    && rm -rf /var/lib/apt/lists/*

COPY start.py /start.py
RUN chmod +x /start.py

ENTRYPOINT ["/start.py"]

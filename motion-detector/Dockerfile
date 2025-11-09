FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY motion_detector.py .

CMD ["python", "motion_detector.py"]

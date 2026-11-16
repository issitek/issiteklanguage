# Bench STT — faster-whisper small (CPU, int8) para la Fase 0
FROM python:3.13-slim
RUN pip install --no-cache-dir faster-whisper==1.2.0 requests==2.32.3 "av>=13,<14"
WORKDIR /app
COPY transcribe.py /app/transcribe.py
ENTRYPOINT ["python", "/app/transcribe.py"]

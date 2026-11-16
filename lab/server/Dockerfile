# Lab server — contexto de build es lab/ (ver docker-compose.yml)
FROM python:3.13-slim

WORKDIR /app

COPY server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY server/ ./server/
COPY client/ ./client/
COPY tests/ ./tests/
WORKDIR /app/server

ENV PYTHONUNBUFFERED=1
EXPOSE 9090
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9090"]

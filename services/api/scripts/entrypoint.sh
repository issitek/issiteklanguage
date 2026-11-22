#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[entrypoint] migraciones"
alembic upgrade head

echo "[entrypoint] seed de contenido A1"
python -m app.seed

if [ "${UVICORN_RELOAD:-false}" = "true" ]; then
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${UVICORN_WORKERS:-1}"

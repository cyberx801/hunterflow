#!/bin/sh
set -e

export UV_CACHE_DIR=/tmp/uv-cache

echo "[hunterflow] applying database migrations"
/venv/bin/alembic upgrade head

echo "[hunterflow] starting $HF_PROCESS"
if [ "$HF_PROCESS" = "worker" ]; then
  exec /venv/bin/python -m app.jobs.worker --processes 2 --threads 8
else
  exec /venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
fi

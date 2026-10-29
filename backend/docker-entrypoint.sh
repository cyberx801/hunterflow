#!/bin/sh
set -e

export UV_CACHE_DIR=/tmp/uv-cache

# Only the API applies migrations. Worker/scheduler wait for the API healthcheck
# (see compose depends_on) so concurrent `alembic upgrade` runs cannot race.
if [ "$HF_PROCESS" = "worker" ] || [ "$HF_PROCESS" = "scheduler" ]; then
  echo "[hunterflow] migrations are applied by the api service"
else
  echo "[hunterflow] applying database migrations"
  /venv/bin/alembic upgrade head
fi

echo "[hunterflow] starting $HF_PROCESS"
if [ "$HF_PROCESS" = "worker" ]; then
  exec /venv/bin/python -m app.jobs.worker --processes 2 --threads 8
elif [ "$HF_PROCESS" = "scheduler" ]; then
  exec /venv/bin/python -m app.jobs.scheduler
else
  exec /venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
fi

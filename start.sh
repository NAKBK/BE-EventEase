#!/bin/sh
set -eu

alembic upgrade head

if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  python -m app.cli seed
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-10000}"

#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "→ [start.sh] Running database migrations..."
alembic upgrade head || {
  echo "✗ Migration failed. Aborting startup."
  exit 1
}

echo "→ [start.sh] Starting uvicorn on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"

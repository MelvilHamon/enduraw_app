#!/usr/bin/env sh
set -e

# Apply database migrations against a (possibly empty) database, then serve.
echo "Running database migrations..."
alembic upgrade head

echo "Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

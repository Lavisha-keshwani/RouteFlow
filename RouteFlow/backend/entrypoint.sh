#!/usr/bin/env bash
set -euo pipefail

# Apply database migrations, then optionally seed demo data.
echo "Running database migrations..."
alembic upgrade head

if [ "${SEED_ON_START:-false}" = "true" ]; then
  echo "Seeding demo data..."
  python -m app.seeds.seed || echo "Seed skipped (already seeded or error)."
fi

echo "Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${WEB_CONCURRENCY:-2}"

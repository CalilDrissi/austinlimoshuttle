#!/usr/bin/env bash
# Wait for the database, apply migrations and role groups, then hand off to the
# container command (runserver by default). migrate and sync_roles are both
# idempotent, so this is safe to run on every boot. Legacy data import and
# superuser creation are one-shot steps run manually — not here.
set -euo pipefail

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-3306}"

echo "==> waiting for database at ${DB_HOST}:${DB_PORT}"
until python -c "import socket; socket.create_connection(('${DB_HOST}', ${DB_PORT}), timeout=2)" 2>/dev/null; do
  sleep 2
done
echo "==> database reachable"

echo "==> migrate"
python manage.py migrate --noinput

echo "==> sync_roles"
python manage.py sync_roles

# Production only (DatabaseCache table + collected static for WhiteNoise). Both
# idempotent, so re-running on every boot is safe.
if [ "${DJANGO_COLLECTSTATIC:-0}" = "1" ]; then
  echo "==> createcachetable"
  python manage.py createcachetable || true
  echo "==> collectstatic"
  python manage.py collectstatic --noinput
fi

exec "$@"

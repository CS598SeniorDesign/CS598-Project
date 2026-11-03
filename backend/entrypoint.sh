#!/bin/sh
set -e

echo "Waiting for database..."
i=0
until out=$(python manage.py check --database default 2>&1); do
  i=$((i+1))
  echo "Database check failed (attempt $i):"
  echo "$out" | tail -n 5
  [ "$i" -ge 30 ] && { echo "Giving up."; exit 1; }
  sleep 2
done

if [ -n "$PROMETHEUS_MULTIPROC_DIR" ]; then
  # Metrics files left by a previous run would be counted again.
  rm -rf "$PROMETHEUS_MULTIPROC_DIR"
  mkdir -p "$PROMETHEUS_MULTIPROC_DIR"
fi

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "Applying database migrations..."
  python manage.py migrate --noinput
fi

echo "Starting application..."
exec "$@"
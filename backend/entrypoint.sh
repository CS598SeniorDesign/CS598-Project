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

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Starting application..."
exec "$@"
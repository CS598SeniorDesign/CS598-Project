#!/bin/sh
set -e

echo "Waiting for database..."
python manage.py wait_for_db 2>/dev/null || {
  until python -c "
  import os, sys, time
  import psycopg2
  for i in range(30):
      try:
          psycopg2.connect(
              dbname=os.environ['DATABASE_NAME'],
              user=os.environ['DATABASE_USERNAME'],
              password=os.environ['DATABASE_PASSWORD'],
              host=os.environ['DATABASE_HOST'],
              port=os.environ['DATABASE_PORT'],
          )
          sys.exit(0)
      except Exception:
          time.sleep(1)
  sys.exit(1)
  "; do
      echo "Database unavailable, retrying..."
      sleep 1
  done
}

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Starting application..."
exec "$@"
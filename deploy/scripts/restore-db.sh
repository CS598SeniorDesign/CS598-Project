#!/bin/sh
# Restore the QuestLog database from a backup made by backup-db.sh. THIS REPLACES ALL CURRENT DATA.
#
# Usage (from the deploy directory):
#   scripts/restore-db.sh backups/questlog-20261201T031500Z.dump
#
# To restore from object storage, first download the dump into ./backups, e.g.:
#   docker run --rm -v "$(pwd)/backups:/backups" <same RCLONE_CONFIG_STORE_* variables as backup-db.sh> \
#     rclone/rclone:1 copy store:<bucket>/database/questlog-<stamp>.dump /backups/
#
# The web app and workers are stopped during the restore and started again afterwards.

set -eu

cd "$(dirname "$0")/.."

dump=${1:-}
if [ -z "$dump" ] || [ ! -s "$dump" ]; then
  echo "Usage: $0 <path to .dump file>" >&2
  exit 1
fi

env_value() {
  grep -E "^$1=" .env | tail -n 1 | cut -d= -f2-
}
DATABASE_NAME=$(env_value DATABASE_NAME)
DATABASE_USERNAME=$(env_value DATABASE_USERNAME)

COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env --env-file .image.env"

printf 'This replaces ALL data in %s with %s. Type the database name to continue: ' "$DATABASE_NAME" "$dump"
read -r answer
if [ "$answer" != "$DATABASE_NAME" ]; then
  echo "Cancelled."
  exit 1
fi

echo "Stopping the app so nothing writes during the restore..."
$COMPOSE stop caddy frontend backend celery-worker celery-beat

echo "Restoring..."
$COMPOSE exec -T db pg_restore -U "$DATABASE_USERNAME" -d "$DATABASE_NAME" --clean --if-exists --no-owner < "$dump"

echo "Starting the app again..."
$COMPOSE up -d
echo "Restore complete. Check https://$(env_value APP_DOMAIN)/health/"

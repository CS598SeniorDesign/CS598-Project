#!/bin/sh
# Back up the QuestLog database to S3-compatible object storage (e.g. Oracle Cloud's free tier), and delete backups
# older than BACKUP_RETENTION_DAYS. Run nightly from cron (see docs/DEPLOYMENT.md):
#
#   15 3 * * * /opt/questlog/scripts/backup-db.sh >> /opt/questlog/backups/backup.log 2>&1
#
# The dump is made with pg_dump inside the db container (custom format, compressed) and uploaded with the rclone
# container, so nothing besides Docker needs installing on the server. The last 7 dumps are also kept locally in
# ./backups for quick restores. Settings come from .env (BACKUP_S3_*).

set -eu

cd "$(dirname "$0")/.."

# Read only the variables this script needs from .env, without executing the file.
env_value() {
  grep -E "^$1=" .env | tail -n 1 | cut -d= -f2-
}

DATABASE_NAME=$(env_value DATABASE_NAME)
DATABASE_USERNAME=$(env_value DATABASE_USERNAME)
BACKUP_S3_ENDPOINT=$(env_value BACKUP_S3_ENDPOINT)
BACKUP_S3_REGION=$(env_value BACKUP_S3_REGION)
BACKUP_S3_BUCKET=$(env_value BACKUP_S3_BUCKET)
BACKUP_S3_ACCESS_KEY_ID=$(env_value BACKUP_S3_ACCESS_KEY_ID)
BACKUP_S3_SECRET_ACCESS_KEY=$(env_value BACKUP_S3_SECRET_ACCESS_KEY)
BACKUP_RETENTION_DAYS=$(env_value BACKUP_RETENTION_DAYS)
BACKUP_RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}

COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env --env-file .image.env"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
file="questlog-${stamp}.dump"

mkdir -p backups
echo "$(date -u) Backing up ${DATABASE_NAME} to backups/${file}"
$COMPOSE exec -T db pg_dump -U "$DATABASE_USERNAME" -d "$DATABASE_NAME" --format=custom --compress=9 > "backups/${file}"

if [ ! -s "backups/${file}" ]; then
  echo "Backup file is empty; aborting." >&2
  rm -f "backups/${file}"
  exit 1
fi

# rclone is configured entirely through environment variables, for a remote named "store".
rclone() {
  docker run --rm \
    -v "$(pwd)/backups:/backups" \
    -e RCLONE_CONFIG_STORE_TYPE=s3 \
    -e RCLONE_CONFIG_STORE_PROVIDER=Other \
    -e RCLONE_CONFIG_STORE_ENDPOINT="$BACKUP_S3_ENDPOINT" \
    -e RCLONE_CONFIG_STORE_REGION="$BACKUP_S3_REGION" \
    -e RCLONE_CONFIG_STORE_ACCESS_KEY_ID="$BACKUP_S3_ACCESS_KEY_ID" \
    -e RCLONE_CONFIG_STORE_SECRET_ACCESS_KEY="$BACKUP_S3_SECRET_ACCESS_KEY" \
    -e RCLONE_CONFIG_STORE_FORCE_PATH_STYLE=true \
    rclone/rclone:1 "$@"
}

if [ -n "$BACKUP_S3_BUCKET" ]; then
  rclone copy "/backups/${file}" "store:${BACKUP_S3_BUCKET}/database/"
  rclone delete --min-age "${BACKUP_RETENTION_DAYS}d" "store:${BACKUP_S3_BUCKET}/database/"
  echo "$(date -u) Uploaded ${file}; removed remote backups older than ${BACKUP_RETENTION_DAYS} days."
else
  echo "BACKUP_S3_BUCKET is not set: kept the backup on this server only." >&2
fi

# Keep only the 7 newest local dumps.
ls -1t backups/questlog-*.dump 2>/dev/null | tail -n +8 | xargs -r rm -f

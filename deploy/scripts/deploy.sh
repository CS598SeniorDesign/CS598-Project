#!/bin/sh
# Deploy a QuestLog release on this server, and roll back automatically if it does not come up healthy.
#
# Usage (from the deploy directory, e.g. /opt/questlog):
#   scripts/deploy.sh <image-tag>        deploy that tag (e.g. sha-1a2b3c4), as the deploy workflow does
#   scripts/deploy.sh --rollback         redeploy the last tag that passed its health checks
#
# The tag is written to .image.env, which docker-compose.prod.yml reads with .env. After a healthy deploy the tag is
# saved to .last-good-tag. If the new release fails its health checks, the previous good tag is redeployed and the
# script exits non-zero so the workflow run fails.
#
# Migrations run when the new backend container starts, while the old containers may still be serving. Keep them
# backward compatible: add columns/tables in one release, remove old ones in a later release.

set -eu

cd "$(dirname "$0")/.."

COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env --env-file .image.env"
HEALTH_TIMEOUT_SECONDS=${HEALTH_TIMEOUT_SECONDS:-300}

if [ ! -f .env ]; then
  echo "Missing .env: copy .env.production.example to .env and fill it in first." >&2
  exit 1
fi

if [ "${1:-}" = "--rollback" ]; then
  tag=$(cat .last-good-tag 2>/dev/null || true)
  if [ -z "$tag" ]; then
    echo "No previous good release recorded in .last-good-tag." >&2
    exit 1
  fi
elif [ -n "${1:-}" ]; then
  tag=$1
else
  echo "Usage: $0 <image-tag> | --rollback" >&2
  exit 1
fi

previous=$(cat .last-good-tag 2>/dev/null || true)

# Health status of a service's container: healthy, starting, unhealthy, or missing.
container_health() {
  id=$($COMPOSE ps -q "$1" 2>/dev/null | head -n 1)
  if [ -z "$id" ]; then
    echo missing
    return
  fi
  docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$id"
}

# Wait until Django, the worker and Next.js report healthy, and Django's readiness check passes.
wait_until_healthy() {
  deadline=$(( $(date +%s) + HEALTH_TIMEOUT_SECONDS ))
  while [ "$(date +%s)" -lt "$deadline" ]; do
    backend=$(container_health backend)
    worker=$(container_health celery-worker)
    frontend=$(container_health frontend)
    echo "  backend=$backend worker=$worker frontend=$frontend"
    if [ "$backend" = healthy ] && [ "$worker" = healthy ] && [ "$frontend" = healthy ]; then
      # /ready/ checks PostgreSQL and Redis from inside Django.
      if $COMPOSE exec -T backend python -c \
        "import urllib.request; urllib.request.urlopen('http://localhost:8000/ready/', timeout=5)" >/dev/null 2>&1; then
        return 0
      fi
    fi
    sleep 5
  done
  return 1
}

# Start a release. A failure here (e.g. an image that cannot be pulled) is not fatal: the health checks then fail and
# the previous release is restored.
start_release() {
  echo "IMAGE_TAG=$1" > .image.env
  $COMPOSE pull --quiet --ignore-pull-failures || true
  $COMPOSE up -d --remove-orphans || true
}

echo "Deploying $tag (previous good release: ${previous:-none})"
start_release "$tag"

if wait_until_healthy; then
  echo "$tag" > .last-good-tag
  # Remove unused images built more than two weeks ago, so old releases do not fill the disk. Recent releases stay, so
  # rolling back to one works offline; rolling back further needs the Deploy workflow (it logs in to the registry).
  docker image prune -af --filter "until=336h" >/dev/null
  echo "Deployed $tag."
  exit 0
fi

echo "Release $tag did not become healthy. Recent backend logs:" >&2
$COMPOSE logs --tail 50 backend >&2 || true

if [ -n "$previous" ] && [ "$previous" != "$tag" ]; then
  echo "Rolling back to $previous" >&2
  start_release "$previous"
  if wait_until_healthy; then
    echo "Rolled back to $previous." >&2
  else
    echo "Rollback to $previous is not healthy either; check the server." >&2
  fi
fi
exit 1

# QuestLog

QuestLog is a web-based platform designed to help board game enthusiasts manage personal game collections, track their play sessions, and analyze gameplay statistics. The platform integrates game tracking, rating, discovery, and community features into a single platform.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Repository Structure](#repository-structure)

## Architecture Overview

QuestLog uses a monorepo split into two top-level applications orchestrated together via Docker Compose:

| Layer | Stack |
| :--- | :--- |
| **Backend** | Django / Django REST Framework, Python 3.12, PostgreSQL 17, Redis (cache, sessions, Celery broker), `uv` for dependency management |
| **Frontend** | Next.js (TypeScript), Tailwind CSS, `output: 'standalone'` build target |
| **Orchestration** | Docker Compose (local dev), multi-stage Dockerfiles per service (`dev` / `production` targets) |
| **CI/CD** | GitHub Actions — linting, type checking, secret scanning, automated tests on every PR |

All backend tool configuration (dependencies, Ruff, mypy, pytest, coverage) lives in `backend/pyproject.toml` as the single source of truth — there are no separate `requirements.txt`, `mypy.ini`, or `pytest.ini` files.

## Repository Structure

```bash
/backend
|- Django project — see backend/README.md for full details
/frontend
|- Next.js project
docker-compose.yml
|- Local development orchestration for db, redis, backend, and frontend
.env.example
|- Template for the root .env file consumed by Docker Compose
.gitignore
|- Single repo-wide ignore file (covers Python, Node, Docker, and OS/editor artifacts)
package.json
|- Root-level tooling: Husky + commitlint (conventional commits enforcement)
```

> **Note:** Husky and commitlint are installed at the **repo root**, not inside `frontend/`. After cloning, run `npm install` from the repository root once — skipping this causes commit hooks to hang silently rather than error clearly.

## Getting Started

1. Clone the repo
2. Install root tooling (required for commit hooks) by running:

    ```bash
    npm install
    ```

3. Set up environment variables — see [Environment Variables](#environment-variables) below.
4. Build and start the Docker containers — see [Running with Docker Compose](#running-with-docker-compose) below.
5. Run migrations:

    ```bash
      docker compose exec backend python manage.py migrate
    ```

### Environment Variables

QuestLog uses **three separate env files**, each with a distinct scope. Do not merge them — this separation is intentional (it keeps backend secrets out of the frontend container, and keeps Docker orchestration variables separate from Next.js's own env-file conventions).

| File | Scope | Consumed by |
| :--- | :--- | :--- |
| `/.env` | Docker Compose orchestration — variable interpolation inside `docker-compose.yml` (e.g. `${DATABASE_NAME}`), and env vars injected into the `db`, `redis`, and `backend` containers | Docker Compose |
| `/backend/.env` | Backend settings when running Django **outside** Docker (e.g. `uv run python manage.py runserver` directly on your host) | `django-environ` via `config/settings.py` |
| `/frontend/.env.local` | Frontend environment variables — Next.js's own built-in convention for local, uncommitted overrides | Next.js (`next dev` / `next build`) |

Copy each template and fill in real values:

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
```

None of the real `.env` / `.env.local` files are committed — only the `*.example` templates. Never commit real secret values.

### Running with Docker Compose

The backend and frontend Dockerfiles are both multi-stage, with separate `dev` and `production` build targets. Local development uses the `dev` target for both, which enables hot-reload (Django's `runserver` and Next.js's `next dev`) via bind-mounted source code.

```bash
docker compose up --build   # Initial run, or after dependency/Dockerfile changes
docker compose up           # Subsequent runs
```

This brings up four services:

- `db` — PostgreSQL 17
- `redis` — Redis (cache, sessions, Celery broker)
- `backend` — Django, served on `:8000`
- `frontend` — Next.js, served on `:3000`

Code changes on your host are picked up automatically without rebuilding the image — dependency changes (`pyproject.toml`/`uv.lock` or `package.json`/`package-lock.json`) do require `docker compose up --build` to take effect, since installed packages live in named Docker volumes layered on top of the bind mounts.

### Accessing Services

**postgreSQL Shell:**

```bash
docker compose exec db psql -U "$DATABASE_USERNAME" -d "$DATABASE_NAME"
```

OR locally

```bash
psql -h localhost -p 5432 -U "$DATABASE_USERNAME" -d "$DATABASE_NAME"
```

**Redis CLI:**

```bash
docker compose exec redis redis-cli -a "$REDIS_PASSWORD"
```

OR locally

```bash
redis-cli -h localhost -p 6379 -a "$REDIS_PASSWORD"
```

**Django GUI:** `http://localhost:8000`

**Frontend app:** `http://localhost:3000`

**Django management commands:**

```bash
docker compose exec backend python manage.py <command>
```

 OR

```bash
docker compose exec backend django-admin <command>
```

## Frontend environment variables

Frontend environment variables are documented in:

```text
frontend/.env.example
```

Copy the example file when configuring a local frontend environment. Do not commit real environment files or secrets.

The frontend Docker image is designed to integrate with the project's Docker Compose environment so that the frontend can run alongside the backend and database services.

## Health Checks

The backend exposes two operational endpoints, wired in `config/urls.py`:

- `GET /health/` — liveness probe
- `GET /ready/` — readiness probe (checks PostgreSQL and Redis connectivity)

The backend's production Docker image includes a `HEALTHCHECK` instruction that polls `/health/` automatically.

## Running Tests & Linting

Run backend checks inside the running container:

```bash
docker compose exec backend uv run ruff check
docker compose exec backend uv run ruff format --check
docker compose exec backend uv run mypy
docker compose exec backend uv run pytest
```

See [`backend/README.md`](backend/README.md) for the full backend command reference, including running these natively (outside Docker) via `uv`.

## Production Builds

Both Dockerfiles include a `production` build target in addition to `dev`:

- **Backend:** installs only production dependencies (`uv sync --no-default-groups --extra prod`, excluding `mypy`/`pytest`/`ruff`/etc.), runs as a non-root user, and serves via `gunicorn`.
- **Frontend:** builds with `output: 'standalone'` and serves via `node server.js` as a non-root user, producing a minimal, self-contained runtime image.

To build and run a production-target image standalone (outside Compose), e.g. for the frontend:

```bash
docker build -t questlog-frontend --target production ./frontend
docker run --rm -p 3000:3000 questlog-frontend
```

The same `--target production` pattern applies to `./backend`.

## Further Documentation

- [`backend/README.md`](backend/README.md) — backend setup, dependency management, app structure, and test commands
- [`frontend/README.md`](frontend/README.md) — frontend setup, dependency management, app structure, and test commands
- `AI_USAGE_LOG.md` — required log of all generative AI usage across this project

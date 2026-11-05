# Backend

This document provides guidance on running the backend through Docker and locally

## Table of Contents

- [Backend](#backend)
  - [Table of Contents](#table-of-contents)
  - [Backend File Structure](#backend-file-structure)
  - [Running via Docker (Recommended)](#running-via-docker-recommended)
  - [Running Locally (Without Docker)](#running-locally-without-docker)
  - [Getting Started](#getting-started)
    - [Quick Setup](#quick-setup)
  - [Virtual Environment](#virtual-environment)
  - [Dependencies](#dependencies)
    - [Dependency Files](#dependency-files)
    - [Installing Dependencies](#installing-dependencies)
    - [Adding New Dependencies](#adding-new-dependencies)
      - [Production Dependencies](#production-dependencies)
      - [Development Dependencies](#development-dependencies)
      - [The `psycopg2` / `psycopg2-binary` Split](#the-psycopg2--psycopg2-binary-split)
    - [Updating the `uv.lock` File](#updating-the-uvlock-file)
  - [Environment Variables](#environment-variables)
  - [Running the Backend](#running-the-backend)
    - [Database Migrations \& Rollbacks](#database-migrations--rollbacks)
    - [Populating Synthetic Test Data](#populating-synthetic-test-data)
    - [Admin Access \& Superuser Creation](#admin-access--superuser-creation)
  - [Creating a new app](#creating-a-new-app)
  - [Running tests](#running-tests)
  - [Health Endpoints](#health-endpoints)
  - [Logging \& Monitoring](#logging--monitoring)
  - [Background Tasks (Celery)](#background-tasks-celery)
  - [Library \& Wishlist API](#library--wishlist-api)
  - [Recommendation Engine](#recommendation-engine)

## Backend File Structure

```bash
/catalog
|- 'Django app for the board game library: game metadata, BGG XML API integration, search/filter, and wishlist models'
/config
|- 'Django project configuration: settings, ASGI/WSGI entrypoint, root urls.py'
/core
|- 'Shared app: health/readiness check views and other cross-app utilities'
/profiles
|- 'Django app for user/player profiles, player and group statistics, derived social tags, and account-level data'
/recommendations
|- 'Django app for the recommendation engine: content-based and collaborative filtering, pgvector embeddings, opt-in settings, and feedback'
/tracking
|- 'Django app for session/play tracking and multi-metric ratings.'
.dockerignore
|- 'Excludes .venv, caches, and real .env files from the Docker build context'
.env.example
|- 'Sanitized template of required environment variables (DB, Redis, Django secret key, hCaptcha keys, etc.) for local setup'
.python-version
|- 'Pins the exact Python version used by uv for this project'
Dockerfile
|- 'Multi-stage build: dev (hot-reload via runserver) and production (gunicorn, minimal image) targets'
manage.py
|- 'Djangos command line utility for running the dev server, migrations, management commands, etc.'
pyproject.toml
|- 'Python project metadata and tool configuration (dependencies, Ruff, mypy, pytest settings)'
README.md
|- 'Project documentation for architecture overview, local setup steps, environment variables'
uv.lock
|- 'Locked dependency versions for reproducible installs via uv'
```

## Running via Docker (Recommended)

For local development the backend is intended to run as part of the full Docker Compose stack defined in the project root. See the [root README](../README.md#running-with-docker-compose) for full setup instructions.

Summary:

```bash
cp .env.example .env  # root env file
docker compose up --build
docker compose exec backend python manage.py migrate
```

The backend container runs Django's `runserver` with source code bind-mounted from `./backend`, so code changes are picked up immediately without rebuilding the image. Installed dependencies live in a named Docker volume layered over the bind mount.

If you add or change a dependency in `pyproject.toml`, run `docker compose up --build` (or `docker compose build backend`) to pick it up.

To run backend management commands, tests, or linting inside the running container:

```bash
docker compose exec backend uv run python manage.py <command>
docker compose exec backend uv run pytest
```

## Running Locally (Without Docker)

If you need to run the backend directly on your host, you'll still need a local PostgreSQL setup and Redis instance available, and a `backend/.env` file pointed at them.

## Getting Started

1. Set up the virtual environment.
See: [Virtual Environment](#virtual-environment)

2. Install dependencies.
See [Dependencies](#dependencies)

3. Set up the environment variables file.
See [Environment Variables](#environment-variables)

4. Run the backend server.
See: [Running the Backend](#running-the-backend)

### Quick Setup

**Local (uv):**
```bash
pip install uv # Run if uv is not already installed. Swap pip install for your systems package management install command
uv sync
```

When the repository is opened in VS Code, select the interpreter at `backend/.venv/bin/python` if it is not selected automatically. The repository workspace settings point Pylance at this interpreter and add `backend/` to its import search path. This must match the environment where `uv sync` installs dependencies.

To verify the environment and imports:

```bash
uv run python -c "import django; print(django.get_version())"
uv run python manage.py check
```

Establish the [database connection](#environment-variables) and continue:

```bash
uv run python manage.py migrate
uv run python manage.py runserver
```

**Docker:**
To launch the complete local development stack (database, Redis, backend, frontend) with a single command:
```bash
docker compose up --build
```

## Virtual Environment

A python virtual environment is needed to prevent package conflicts and isolate your dependencies from other developers. This project uses uv to manage dependencies and the virtual environment. Python is pinned to **Python 3.12** via `.python-version` matching the version used in CI and in the Docker images. Running project against a different locally-installed Python versions will cause issues.

Running:

```bash
uv sync
```

will automatically:

- Create a .venv virtual environment if one does not already exist
- Install all dependencies defined in pyproject.toml
- Synchronize installed packages to the versions locked in uv.lock

Most project commands should be run using uv. Example:

```bash
uv run pytest
uv run python manage.py runserver
```

## Dependencies

### Dependency Files

This project uses `pyproject.toml` and `uv.lock` instead of `requirements.txt` and `requirements.in` files. `pyproject.toml` contains the project dependencies and `uv.lock` contains the fully resolved and reproducible dependency graph used by developers, Docker, and the CI/CD pipeline.

### Installing Dependencies

To install dependencies, run:

```bash
uv sync # Installs base deps and the dev group
uv sync --no-dev # Installs only base dependencies
```

To ensure dependencies match the locked file, run:

```bash
uv sync --locked
```

### Adding New Dependencies

Dependencies are defined in `pyproject.toml` in dependency groups. The base dependencies are those required for production runtime environments. The `dev` dependency groups contains dependencies required for development. The `prod` optional-dependency group contains dependencies required only in the production Docker image.

#### Production Dependencies

To add a runtime dependency:

```bash
uv add <package>
```

Example

```bash
uv add django-filter
```

#### Development Dependencies

To add a development-only dependency:

```bash
uv add --dev <package>
```

Example

```bash
uv add --dev pytest-mock
```

#### The `psycopg2` / `psycopg2-binary` Split

This project intentionally uses **two different PostgreSQL drivers** depending on context, per supply-chain security best practice, they should never both be installed into the same environment:

- **`psycopg2-binary`** (in the `dev` group) - a prebuilt wheel, fast and convenient for local development.
- **`psycopg2`** (in the `prod` optional-dependency group) - compiled from source at install time, used in the production Docker image.

The production Docker build installs with `--no-default-groups --extra prod`, which pulls in `psycopg2` and excludes `psycopg2-binary` entirely. Local `uv sync` pulls in the `dev` group, which includes `psycopg2-binary`. Do not add `psycopg2-binary` to base `dependencies`, it will conflict with `psycopg2` in any environment that installs both.

### Updating the `uv.lock` File

Any dependency changes automatically update `pyproject.toml` and `uv.lock`

To regenerate the `uv.lock` file manually, run:

```bash
uv lock
```

Ensure you commit both the updated `pyproject.toml` and `uv.lock` files. A stale `uv.lock` will fail `uv sync --locked` in both CI and Docker builds.

## Environment Variables

**Note:** Do not commit the environment variables to the repository, they must remain private.

1. Create a `.env` file with the contents of the `.env.example` file by running the following while in the root directory: `cp .env.example ./backend/.env`
2. Fill in the missing values as needed.

Considerations:

- You will need a local PostgreSQL and Redis instance running, with `DATABASE_HOST`/`REDIS_*_URL` values pointed at them (the `.env.example` defaults assume Docker service names like `db` and `redis`, which only resolve inside the Docker network).
- If running via Docker Compose, environment variables instead come from the **root** `.env` file — see the [root README](../README.md#environment-variables) for details on how the two files differ in scope.

## Running the Backend

Before running, make sure your database has the proper migrations.

**Local (uv):**
```bash
uv run python manage.py migrate
```

**Docker:**
```bash
docker compose exec backend uv run python manage.py migrate
```

To run the server:

**Local (uv):**
```bash
uv run python manage.py runserver # Defaults to port 8000
uv run python manage.py runserver 8001 # This will run the django server on localhost port 8001
```
*(Note: Docker automatically runs the server using the compose file).*

### Database Migrations & Rollbacks

Treat committed migration files as the source-controlled schema history. Before opening a pull request, run the following checks from `backend/`:

```bash
# Fails if model changes would generate an uncommitted migration.
uv run python manage.py makemigrations --check --dry-run

# Fails for unsafe or non-reversible migration operations.
uv run python manage.py lintmigrations --include-apps catalog profiles tracking users

# Fails if the configured database has unapplied migrations.
uv run python manage.py migrate --check
```

```bash
uv run python manage.py makemigrations
uv run python manage.py showmigrations --plan
```

To test down-migrations (rollbacks) for a specific app, target the `zero` migration state to clear it.

**Local (uv):**
```bash
uv run python manage.py migrate tracking zero
uv run python manage.py migrate profiles zero
uv run python manage.py migrate catalog zero
```

**Docker:**
To reset the entire database:
```bash
docker compose down -v
```
For specific apps:
```bash
docker compose exec backend uv run python manage.py migrate tracking zero
docker compose exec backend uv run python manage.py migrate profiles zero
docker compose exec backend uv run python manage.py migrate catalog zero
```

### Populating Synthetic Test Data

To populate your local database with mock users, board games, library items, ratings, play sessions, and recommendation settings for development testing, run our custom seeder command. The mock data can be seen with the backend API running at `http://localhost:8000/admin/`.

**Local (uv):**
```bash
uv run python manage.py seed
```

**Docker:**
```bash
docker compose exec backend uv run python manage.py seed
```

### Admin Access & Superuser Creation
You can access the Django admin dashboard at `http://localhost:8000/admin/`.

**Manual Creation**

**Local (uv):**
```bash
uv run python manage.py createsuperuser
```

**Docker:**
```bash
docker compose exec backend uv run python manage.py createsuperuser
```

## Creating a new app

To start a new app, run the following command in the backend directory

```bash
uv run python manage.py startapp [app_name]
```

- Add the app to `INSTALLED_APPS` in config/settings.py
- Create a urls.py file in your new app
- Add your app urls to config/urls.py

## Running tests

The following commands can be run to lint, format, and run tests in the backend

```bash
uv run ruff check          # Linting
uv run ruff format --check # Formatting
uv run complexipy . --max-complexity-allowed 10 --exclude migrations --exclude tests
uv run ruff check . --select C901 --exclude migrations
uv audit         # Known Python dependency vulnerabilities
uv run mypy                # Type checking
uv run pytest              # Unit testing
```
The backend enforces a maximum cyclomatic complexity of 10 with Ruff and a maximum cognitive complexity of 10 with Complexipy. These same caps run in the `backend-lint` CI job.

Pull requests run `uv audit` against the locked backend environment and fail when known dependency vulnerabilities are found.
Minimum coverage threshold is enforced at 60% (`--cov-fail-under=60` via `[tool.coverage.report]` in `pyproject.toml`).

CI publishes complete backend and frontend test logs plus their coverage reports as workflow artifacts. The
workflow finds issues referenced by the associated pull request's closing keywords (`Closes`, `Fixes`, or
`Resolves`) and posts a combined CI validation report covering tests, coverage, linting, the Docker smoke test,
secret scanning, and artifact links to each linked issue after every run.

The same commands can be run inside the Docker `dev` container via `docker compose exec backend uv run <command>` — see the [root README](../README.md#running-tests--linting).

## Health Endpoints

Two operational endpoints are wired via `config/urls.py` and implemented in `core/views.py`:

- `GET /health/` — liveness probe (confirms the process is up)
- `GET /ready/` — readiness probe (confirms PostgreSQL and Redis are reachable)

Both use trailing slashes intentionally, to avoid Django's `APPEND_SLASH` redirect behavior causing flaky results when polled by Docker healthchecks or uptime monitors.

## Logging & Monitoring

**Structured logs** (`core/structured_logging.py`, `core/middleware.py`). Every log line is one JSON object with `timestamp` (UTC), `level`, `logger`, `message`, `request_id` and `user_id`, plus any fields passed with `extra=`:

```json
{"timestamp": "2026-11-01T20:24:52.272+00:00", "level": "WARNING", "logger": "questlog.request", "message": "GET /api/v1/recommendations/ 403", "request_id": "974fbe35...", "user_id": null, "method": "GET", "route": "api/v1/recommendations/", "status": 403, "duration_ms": 0.77}
```

- `RequestContextMiddleware` gives each request an ID, reusing a well-formed incoming `X-Request-ID` header (so the frontend or a proxy can correlate) and returning it in the response's `X-Request-ID` header. The request ID and the signed-in user's ID are attached to every log line written during the request, from any logger. Both are `null` outside requests (management commands).
- The `questlog.request` logger writes one access line per request (INFO for 2xx/3xx, WARNING for 4xx, ERROR for 5xx). `/health/`, `/ready/` and `/metrics/` are not logged unless they fail.
- The `questlog.security` logger records sign-ins, failed sign-ins, sign-outs, sign-ups, password changes and resets, and MFA authenticators added, removed or failed (`core/signals.py`). Events identify users by ID only; failed sign-ins never log the email address that was tried.
- `LOGLEVEL` sets the level (default `info`). `LOG_FORMAT=text` switches to human-readable lines for local debugging.
- Never log emails, passwords, tokens or other personal data. Use `user_id` to identify users.

**Metrics** (`core/metrics.py`). `GET /metrics/` serves Prometheus metrics to callers sending `Authorization: Bearer <METRICS_TOKEN>`; it returns 404 when `METRICS_TOKEN` is unset.

| Metric | What it measures |
| :--- | :--- |
| `questlog_http_requests_total`, `questlog_http_request_duration_seconds` | Requests and latency by method, URL pattern and status |
| `questlog_dependency_up` | Whether PostgreSQL and Redis passed the last `/ready/` check |
| `questlog_external_api_requests_total`, `questlog_external_api_request_duration_seconds` | BoardGameGeek API calls by endpoint and outcome |
| `questlog_security_events_total` | Security events by type (e.g. alert on a spike in `login_failed`) |
| `questlog_recommendation_requests_total` | Recommendation requests by requested and served strategy, fallback reason, and result cache hit/miss |
| `questlog_recommendation_compute_seconds` | Time to compute recommendations on a cache miss |
| `questlog_recommender_model_build_seconds` | Time to build the content model, collaborative model and embeddings |

The production image runs gunicorn with `config/gunicorn.conf.py` and sets `PROMETHEUS_MULTIPROC_DIR`, so `/metrics/` reports totals across all workers. To collect metrics locally, set `METRICS_TOKEN` in `.env` and start the optional Prometheus container (configured in `monitoring/prometheus.yml`), then open `http://localhost:9090`:

```bash
docker compose --profile monitoring up
```

## Background Tasks (Celery)

Slow and scheduled work runs in [Celery](https://docs.celeryq.dev/) workers instead of web requests, with Redis database 2 as the broker and result store. The app is defined in `config/celery.py`, and each Django app keeps its tasks in `tasks.py`.

| Task | Runs | What it does |
| :--- | :--- | :--- |
| `tracking.tasks.sync_bgg_plays` | When a user calls `POST /api/v1/plays/sync/` | Imports the user's BGG plays. Retries up to 3 times (1, 2, 4 minutes apart) when BGG is down or rate limiting; client errors are not retried. |
| `tracking.tasks.sync_bgg_collection` | When a user calls `POST /api/v1/library/sync/` | Imports the games the user owns or wishlists on BGG. Retries every 15–120 seconds (about 9 minutes in all) while BGG prepares the collection, and on outages. |
| `tracking.tasks.purge_removed_library_items` | Daily, 02:30 UTC | Permanently deletes library and wishlist entries removed more than `LIBRARY_ITEM_RETENTION_DAYS` (default 90) ago |
| `recommendations.tasks.refresh_recommender_caches` | Every 30 minutes | Rebuilds the cached content and collaborative models before they expire, so requests rarely build them |
| `recommendations.tasks.train_recommender` | Daily, 03:00 UTC | `manage.py train_recommender`: models, pgvector embeddings, offline evaluation, experiment tracking |
| `recommendations.tasks.recommendation_report` | Mondays, 04:00 UTC | `manage.py recommendation_report --days 7` |

The schedule is `CELERY_BEAT_SCHEDULE` in `config/settings.py`. Scheduled tasks hold a lock while they run, so a slow run is skipped by the next one rather than overlapped.

**Play sync API.** `POST /api/v1/plays/sync/` returns `202 Accepted` with a `task_id` and `status_url` (also in the `Location` header) instead of waiting for the import. Poll `GET /api/v1/plays/sync/<task_id>/` for its `status` (`queued`, `running`, `retrying`, `succeeded`, `failed`), `detail` message and number of plays `imported`. Each user has at most one import queued or running; syncing again returns the same task. Only the user who started an import can see its status, which is kept for 24 hours.

**Running it.** `docker compose up` starts three extra containers from the backend image:

- `celery-worker` runs tasks (2 processes). Celery does not reload on code changes, so run `docker compose restart celery-worker celery-beat` after editing tasks.
- `celery-beat` queues the scheduled tasks. Run exactly one beat, or every scheduled task is queued twice.
- `flower` is a web UI for workers, tasks, retries and failures at <http://localhost:5555> (bound to localhost only). Set `FLOWER_BASIC_AUTH=user:password` in `.env` to require a login. Flower also serves Prometheus metrics for tasks at `/metrics`.

These containers set `RUN_MIGRATIONS=false` so only the web container runs migrations. In production, run the worker and beat from the production image the same way, overriding its command:

```bash
celery -A config worker --loglevel=INFO
celery -A config beat --loglevel=INFO --schedule=/tmp/celerybeat-schedule
```

Without Docker, start a worker in another terminal: `uv run celery -A config worker --loglevel=INFO`. On macOS, add `--pool=solo`; Celery's default process pool fails there with `ValueError: not enough values to unpack`. Alternatively, set `CELERY_TASK_ALWAYS_EAGER=True` to run tasks inline in the web process, with no worker (development only: requests then wait for the task again).

**Logs.** Workers write the same JSON log lines as the web app. A task queued during an API request keeps that request's `request_id` and `user_id` and adds `task_id` and `task_name`, so you can follow an import from the request that started it. The `questlog.tasks` logger records each task's start, finish (state and `duration_ms`) and failures with stack traces.

**Tests** never need a worker or broker: tests mock `apply_async`, or run tasks in-process with `.apply()`.

## Library & Wishlist API

`/api/v1/library/` holds each user's owned games (`ownership=OWNED`) and wishlist (`WISHLISTED`), looked up by BGG ID. Every user only sees their own entries.

| Endpoint | Purpose |
| :--- | :--- |
| `GET /library/` | List entries. Filters: `ownership`, `is_played`, `has_played`, `search`. Sort: `ordering=added_at\|name\|rating\|rank\|play_count\|last_played\|priority` (prefix `-` for descending; default `-added_at`; missing values sort last). |
| `POST /library/` | Add a game (`game_id`, optional `ownership`, `is_played`, `wishlist_priority`, `house_rules`). The game must already be in the catalog (`GET /games/{bgg_id}/` caches it). 409 if already added. |
| `GET/PATCH/DELETE /library/{bgg_id}/` | Read, change, or remove an entry. Removing soft-deletes it; re-adding within the retention period restores it. |
| `GET /library/summary/` | `owned`, `wishlisted`, `owned_unplayed`, `wishlisted_unplayed`, `total`. |
| `POST /library/sync/` → `GET /library/sync/{task_id}/` | Import the BGG collection in the background (202 + task ID, then poll), like `POST /plays/sync/`. |

**Played status.** Each entry reports `is_played` (the user's own flag, e.g. for games played before using QuestLog), `play_count` and `last_played` (from the user's logged and imported plays), and `has_played` (either). Clients should display `has_played`, so a logged play counts even if the user never set `is_played` (the current frontend still shows `is_played`).

**Wishlist priority.** `wishlist_priority` uses BoardGameGeek's scale: 1 must have, 2 love to have, 3 like to have, 4 thinking about it, 5 don't buy this. It can only be set on wishlisted entries and is cleared when a game moves to the library.

**Pagination** is opt-in so the current frontend, which loads the whole library, keeps working: pass `?page=` and/or `?page_size=` (default 50, max 200) to get `{count, next, previous, results}`.

**BGG collection import** only adds information. Games owned or wishlisted on BGG are added, owned wins over wishlisted, and BGG plays mark a game played. Existing entries can move from wishlist to library, become played, or gain a priority, but nothing is ever downgraded, and house rules are untouched. Games the user removed in QuestLog are not re-added. Games marked only as previously owned or for trade are skipped. Expansions are excluded. Games missing from the catalog are fetched from BGG one at a time, so a large first import takes a while. Play and collection syncs share the 3-per-minute BGG sync throttle.

`house_rules` is limited to 5,000 characters.

## Recommendation Engine

The `recommendations` app serves game recommendations at `GET /api/v1/recommendations/?strategy=<strategy>`. `GET /api/v1/recommendations/options/` lists every strategy with its parameters, plus the choices for the decision chart and onboarding form.

**Phase I: content-based filtering** (`recommendations/content.py`, pandas + scikit-learn). Each game becomes a TF-IDF weighted vector of its categories, mechanics, and designers, plus scaled player counts, play time, and complexity (BGG `averageweight`). A user's taste is built in the same space from games they rated, played, own, or reacted to, and from their optional onboarding answers. Games are ranked by cosine similarity to that taste.

**Phase II: collaborative filtering** (`recommendations/collaborative.py`, Surprise SVD). A biased matrix factorization learns user and game factors from every opted-in user's interaction scores (ratings, likes/dislikes, plays, ownership), so a game can be recommended because players with similar histories enjoyed it even when it shares no tags with anything the user played. Personalized rankings blend content and collaborative scores, trusting the collaborative model more as it sees more of the user's activity (up to 60%). `players_like_you` uses the collaborative model alone. It trains once there are at least 3 opted-in users and 10 interactions; until then, and for users it has not seen yet, recommendations use Phase I alone.

**Phase III: advanced recommenders** (`recommendations/embeddings.py`, pgvector). Each game gets a 64-dimension hybrid embedding: its content features and collaborative factors, reduced with truncated SVD. Embeddings are stored in the `GameEmbedding` table behind an HNSW cosine index. `for_you` works in two stages: it retrieves the 200 unseen games nearest the user's embedding (the like-weighted average of games they know, computed per request and never stored), then ranks them by hybrid taste score plus embedding similarity. `similar_games?game_id=<bgg id>` returns a game's nearest neighbors and uses no personal data. Embeddings are only built by `train_recommender`; until then both strategies fall back to Phases I and II.

The database needs the pgvector extension. `docker-compose.yml` and CI use the `pgvector/pgvector:pg17` image, and migration `recommendations/0002` runs `CREATE EXTENSION vector`. If your test database predates this change, run pytest once with `--create-db`.

**Privacy.** Users start opted out (`PATCH /api/v1/recommendations/profile/` with `use_personal_data`). Strategies that read a user's own data fall back to basic strategies (`popular`, then `top_rated`) until they opt in, and the response explains why in `fallback_reason`.

**Feedback.** `POST /api/v1/recommendations/feedback/` with `game_id` and `sentiment` (`LIKE`/`DISLIKE`). Disliked games are never recommended again, and both reactions feed the user's taste.

**Caching.** Results are cached in Redis per user for 10 minutes. Saving a library item, rating, play, feedback, or setting clears that user's cache. The content model is cached for an hour, or until the catalog grows. The collaborative model is cached for an hour, or until a user opts in or out, so an opted-out user's data stops shaping other users' recommendations on the next request. Both are built on demand. Celery beat refreshes both every 30 minutes and runs the full `train_recommender` (models and stored game embeddings) nightly; see [Background Tasks](#background-tasks-celery). An opted-out user's activity stays in the stored embeddings until the next nightly run. To rebuild by hand (`--skip-embeddings` rebuilds only the cached models):

```bash
uv run python manage.py train_recommender
```

**Phase IV: monitoring** (`recommendations/evaluation.py`, `recommendations/experiments.py`, MLflow + Weights & Biases).

- *Offline evaluation.* Each `train_recommender` run holds out 20% of opted-in users' interactions, trains the collaborative model on the rest, and measures RMSE, MAE, precision@10 and recall@10 on the held-out part (a game counts as liked at a score of 4 or more). The split is fixed, so a drop between runs means the model or data got worse, not that the split changed. `--skip-evaluation` skips it.
- *Online feedback.* `recommendation_report` counts likes and dislikes per strategy (each reaction records the strategy that produced it) and reports the like rate for each:

  ```bash
  uv run python manage.py recommendation_report --days 30
  ```

- *Experiment tracking.* Both commands send their run (model parameters, data sizes, build times, evaluation metrics or like rates) to every tracker in `RECOMMENDER_TRACKERS`: `log` (a JSON log line; the default), `mlflow` and `wandb`. MLflow and W&B are optional so the backend image stays small; install them with `uv sync --extra monitoring`. MLflow writes to `MLFLOW_TRACKING_URI` (for example `sqlite:///mlflow.db` locally, or an MLflow server's URL), under the `MLFLOW_EXPERIMENT_NAME` experiment. W&B defaults to `WANDB_MODE=offline`, which saves runs to disk without contacting W&B (upload later with `wandb sync`). Set `online` and `WANDB_API_KEY` to send them straight away. A tracker that is missing or fails is logged and skipped, so tracking problems never stop the models from being rebuilt. Runs contain only configuration and aggregate numbers, never personal data.

Serving health (request volume, fallbacks, cache hit rate, latency, model build times) is in the Prometheus metrics above.

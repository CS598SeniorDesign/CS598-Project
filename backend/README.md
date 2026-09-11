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
  - [Creating a new app](#creating-a-new-app)
  - [Running tests](#running-tests)
  - [Health Endpoints](#health-endpoints)

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

```bash
pip install uv # Run if uv is not already installed. Swap pip install for your systems package management install command
uv sync
```

Establish the [database connection](#environment-variables) and continue:

```bash
uv run python manage.py migrate
uv run python manage.py runserver
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

Before running, make sure your database has the proper migrations, using:

```bash
uv run python manage.py migrate
```

To run the server:

```bash
uv run python manage.py runserver # Defaults to port 8000
uv run python manage.py runserver 8001 # This will run the django server on localhost port 8001
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
uv run mypy                # Type checking
uv run pytest              # Unit testing
```

Minimum coverage threshold is enforced at 60% (`--cov-fail-under=60` via `[tool.coverage.report]` in `pyproject.toml`).

The same commands can be run inside the Docker `dev` container via `docker compose exec backend uv run <command>` — see the [root README](../README.md#running-tests--linting).

## Health Endpoints

Two operational endpoints are wired via `config/urls.py` and implemented in `core/views.py`:

- `GET /health/` — liveness probe (confirms the process is up)
- `GET /ready/` — readiness probe (confirms PostgreSQL and Redis are reachable)

Both use trailing slashes intentionally, to avoid Django's `APPEND_SLASH` redirect behavior causing flaky results when polled by Docker healthchecks or uptime monitors.

# Backend

This document provides guidance on running the backend

## Table of Contents

- [Backend](#backend)
  - [Table of Contents](#table-of-contents)
  - [Backend File Structure](#backend-file-structure)
  - [Getting Started](#getting-started)
    - [Quick Setup](#quick-setup)
  - [Virtual Environment](#virtual-environment)
  - [Dependencies](#dependencies)
    - [Dependency Files](#dependency-files)
    - [Installing Dependencies](#installing-dependencies)
    - [Adding New Dependencies](#adding-new-dependencies)
      - [Production Dependencies](#production-dependencies)
      - [Development Dependencies](#development-dependencies)
    - [Updating the `uv.lock` File](#updating-the-uvlock-file)
  - [Environment Variables](#environment-variables)
  - [Running the Backend](#running-the-backend)
  - [Creating a new app](#creating-a-new-app)

## Backend File Structure

```bash
/catalog
└── 'Django app for the board game library: game metadata, BGG XML API integration, search/filter, and wishlist models'
/config
└── 'Django project configuration: settings, ASGI/WSGI entrypoint, root urls.py'
/profiles
└── 'Django app for user/player profiles, player and group statistics, derived social tags, and account-level data'
/tracking
└── 'Django app for session/play tracking and multi-metric ratings.'
.env.example
└── 'Sanitized template of required environment variables (DB, Redis, Django secret key, hCaptcha keys, etc.) for local setup'
.python-version
└── 'Pins the exact Python version used by uv for this project'
manage.py
└── 'Djangos command line utility for running the dev server, migrations, management commands, etc.'
pyproject.toml
└── 'Python project metadata and tool configuration (dependencies, Ruff, mypy, pytest settings)'
README.md
└── 'Project documentation for architecture overview, local setup steps, environment variables'
uv.lock
└── 'Locked dependency versions for reproducible installs via uv'
```

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

A python virtual environment is needed to prevent package conflicts and isolate your dependencies from other developers. This project uses uv to manage dependencies and the virtual environment.

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

This project uses `pyproject.toml` and `uv.lock` instead of `requirements.txt` and `requirements.in` files. `pyproject.toml` contains the project dependencies and `uv.lock` contains the fully resolved and reproducible dependency graph used by developers and the CI/CD pipeline.

### Installing Dependencies

To install dependencies, run:

```bash
uv sync # Installs all dependencies groups
uv sync --no-dev # Installs only runtime dependencies
```

To ensure dependencies match the locked file, run:

```bash
uv sync --locked
```

### Adding New Dependencies

Dependencies are defined in `pyproject.toml` in dependency groups. The base dependencies are those required for production runtime environments. The `dev` dependency groups contains dependencies required for development.

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

### Updating the `uv.lock` File

Any dependency changes automatically update `pyproject.toml` and `uv.lock`

To regenerate the `uv.lock` file manually, run:

```bash
uv lock
```

Ensure you commit both the updated `pyproject.toml` and `uv.lock` files.

## Environment Variables

**Note:** Do not commit the environment variables to the repository, they must remain private.

1. Create a `.env` file with the contents of the `.env.example` file by running the following while in the backend directory: `cp .env.example .env`
2. Fill in the missing values as needed.

Considerations:

- You may need to create a local database for the database variables during development.

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

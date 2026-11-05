FROM python:3.12-slim AS base

RUN mkdir /app
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Pinned to a minor version so a new uv release cannot change how the image builds without a deliberate update.
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /uvx /usr/local/bin/
COPY pyproject.toml uv.lock /app/

FROM base AS dev
RUN uv sync --locked --no-install-project

ENV PATH="/app/.venv/bin:$PATH"
ENV DJANGO_SETTINGS_MODULE=config.settings

COPY . .
RUN chmod +x entrypoint.sh

ENTRYPOINT ["sh", "./entrypoint.sh"]

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM base AS builder
# psycopg2 is compiled from source in production (see "The psycopg2 / psycopg2-binary Split" in README.md), which needs a
# C compiler and the PostgreSQL client headers. They stay in this stage; the final image only gets the runtime library.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*
RUN uv sync --locked --no-install-project --no-default-groups --extra prod

FROM python:3.12-slim AS production
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -r appuser \
    && mkdir /app \
    && chown -R appuser /app

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app
COPY --chown=appuser:appuser . .
RUN chmod +x entrypoint.sh

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings
# Lets gunicorn's workers share Prometheus metrics (see core/metrics.py). entrypoint.sh clears it on startup.
ENV PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus

# The commit the image was built from, reported to Sentry so errors are tied to the release that caused them.
ARG GIT_SHA=unknown
ENV SENTRY_RELEASE=$GIT_SHA

# Settings require these at import time. These placeholder values exist only for this command; the real ones come
# from the environment at runtime.
RUN DJANGO_SECRET_KEY=collectstatic-only ALLOWED_HOSTS=localhost DATABASE_PASSWORD=collectstatic-only \
    python manage.py collectstatic --noinput

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')" || exit 1

ENTRYPOINT ["sh", "entrypoint.sh"]
CMD ["gunicorn", "--config", "config/gunicorn.conf.py", "--bind", "0.0.0.0:8000", "--workers", "3", "config.wsgi:application"]
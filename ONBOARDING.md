# QuestLog Developer Onboarding Guide

Welcome to QuestLog! This guide gets a new contributor from a fresh clone to a running local stack, and orients you to how the codebase and team workflow are organized. It satisfies the Prototype 1 requirement for a developer onboarding guide covering system folders and OOP design patterns.

For deeper background — architecture decisions, sprint history, meeting notes — see the team's [Confluence space](https://cs598spring2026.atlassian.net/wiki/spaces/SD/overview). This document intentionally stays lean; Confluence is the source of truth for anything narrative or historical, this file is the source of truth for "how do I get running and where does code go."

---

## 1. Prerequisites

Install these before cloning:

| Tool | Version | Notes |
| --- | --- | --- |
| Docker & Docker Compose | Latest stable | Required for single-command local orchestration |
| Node.js | 22 (Active LTS) | Match the version pinned in `.nvmrc` / `package.json` engines |
| Python | 3.12 | Only needed if you run backend tooling outside Docker |
| `uv` | Latest | Backend dependency manager — [install docs](https://docs.astral.sh/uv/getting-started/installation/) |
| Git | Latest | — |

You do **not** need PostgreSQL, Redis, or Node installed natively — Docker Compose provisions all of that. Native installs are only useful for running linters/tests directly in your editor.

---

## 2. Clone & First-Time Setup

```bash
git clone https://github.com/CS598SeniorDesign/CS598-Project.git
cd CS598-Project

# Root-level tooling (commitlint + Husky git hooks) — required once per clone
npm install

# Copy and fill in environment templates
cp .env.example backend/.env
cp frontend/.env.example frontend/.env
```

> **Important:** Running `npm install` at the repo root is not optional — it installs the Husky hooks that enforce Conventional Commits on every commit. Skipping this means your commits won't be linted locally (CI will still catch it, but you'll get a slower feedback loop).

### Launching the stack

```bash
docker compose up
```

This brings up `db` (Postgres 17), `redis`, and `backend` (Django/DRF via Gunicorn). The backend will be reachable at `http://localhost:8000` and the frontend will be reachable at `http://localhost:3000`.

### Verifying it worked

- Backend health: `curl http://localhost:8000/health/` (note the trailing slash — `APPEND_SLASH` will redirect and can make health checks look flaky without it)
- Django admin: `http://localhost:8000/admin/`
- Frontend: `http://localhost:3000/api/health`

---

## 3. Repository Structure

```bash
questlog/
├── backend/                  # Django/DRF API
│   ├── config/
│   │   └── settings.py       # Single settings file — no base/dev/prod split
│   ├── <app_name>/           # Django apps, one per bounded domain (e.g. games, sessions, users)
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── permissions.py
│   │   ├── tests/
│   │   └── migrations/
│   ├── Dockerfile            # Multi-stage build
│   ├── pyproject.toml        # Single source of truth: mypy, pytest, Ruff config
│   └── uv.lock
├── frontend/                  # Next.js (TypeScript) app
│   ├── app/                   # Routing
│   ├── components/
│   ├── lib/                   # API clients, utilities
│   ├── .env.local
│   ├── next.config.ts
│   └── Dockerfile
├── recs/                      # Python ML recommendation engine (LightFM, Surprise, pgvector)
├── .github/workflows/         # ci.yml, deploy.yml, release-image.yml
├── docker-compose.yml
├── AI_USAGE_LOG.md
└── pyproject.toml / package.json  # Root-level tooling (commitlint/Husky)
```

**Rule of thumb:** if you're adding config, it goes in the single root or app-level `pyproject.toml` / `settings.py` — we deliberately avoid scattering config across `mypy.ini`, `pytest.ini`, `setup.cfg`, or split settings modules. A stray `pytest.ini` has silently overridden `pyproject.toml` before; if your test config seems ignored, check for one.

---

## 4. OOP Design Patterns & Code Conventions

**Backend (Django/DRF):**

- Business logic belongs in model methods, manager classes, or dedicated service classes — not in views. Views/viewsets stay thin: parse request, call a service/manager, serialize response.
- One `ModelSerializer` per model shape; use nested serializers for related data rather than hand-rolling dicts.
- Custom permission classes subclass `BasePermission`; don't inline permission logic in views.
- Repository-style data access classes are encouraged for complex queries (keeps ORM query logic out of views and testable in isolation).
- Type everything you reasonably can — `mypy` + `django-stubs` + `djangorestframework-stubs` run in CI. If you hit a Ruff `RUF012` (mutable class attribute) conflict with DRF/django-stubs base classes, don't fight it with `ClassVar` — it's already suppressed via `per-file-ignores` for `**/views.py` in `pyproject.toml`.
- Soft deletes: never hard-delete user data. Use `deleted_at` timestamp fields per the Prototype 2 data privacy requirement.

**Frontend (Next.js/TypeScript):**

- Component-per-file, colocate component-specific styles/tests.
- Shared API-calling logic goes in `lib/`, not duplicated in components.
- Prefer composition over deeply nested prop-drilling; lift state only as high as it needs to go.

**Cross-cutting:**

- Docstrings/JSDoc on anything non-obvious, especially service classes and API clients.
- No secrets in code — ever. TruffleHog scans every PR; if it flags a false positive, don't work around it silently, flag it in the PR.

---

## 5. Environment Variables

The backend uses **discrete `DATABASE_*` variables** and `DJANGO_SECRET_KEY` — not a combined `DATABASE_URL` or bare `SECRET_KEY`. Match `backend/.env.example` exactly; CI and Docker Compose both expect this shape.

Key variables (see `.env.example` for the full sanitized template):

| Variable | Used by |
| --- | --- |
| `DJANGO_SECRET_KEY` | Django |
| `DATABASE_ENGINE`, `DATABASE_NAME`, `DATABASE_USERNAME`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT` | Django ORM |
| `REDIS_CACHE_URL`, `REDIS_PASSWORD` | Django cache / Celery / Redis container |
| `ALLOWED_HOSTS`, `DEBUG`, `LOGLEVEL` | Django runtime |
| `NEXT_PUBLIC_*` | Frontend — note these get baked in at **build time** for the production standalone image, so changing them requires a rebuild, not just a container restart |

`env_file` is how services get their variables in `docker-compose.yml` — avoid adding a redundant `environment:` block alongside it, since having both invites precedence bugs (which var wins isn't always obvious). If you notice `db`, `redis`, or `backend` currently declaring both, that's a known cleanup item, not intentional design.

---

## 6. Everyday Workflow

**Branching:** `feature/* → main → testing → production`. Branch names must match `^(feature|bugfix|hotfix|release|refactor|docs|chore)\/[a-z0-9._-]+$`.

**Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, etc.), enforced by commitlint + Husky at the repo root.

**PRs:**

- Link the GitHub Issue with `Closes #N`.
- At least one peer approval required before merge (`main` is protected).
- CI must be green: lint, type check, migration lint, pytest with coverage gate, Docker smoke test, secret scan.

**Running things locally without Docker (backend):**

```bash
cd backend
uv sync --locked
uv run manage.py migrate
uv run pytest
uv run ruff check .
uv run mypy .
```

**Issue tracking:** Jira holds Epic/Story-level planning; GitHub Issues track granular tasks/bugs and are the graded evidence trail. The GitHub-for-Jira integration links branch activity to Jira tickets automatically — reference the Jira ticket key in your branch or PR description when relevant.

**AI usage:** Every meaningful AI-assisted change needs an entry in `AI_USAGE_LOG.md` (exact prompt, output summary, human modifications, verification method). Don't skip this — it's graded.

---

## 7. CI/CD Pipeline at a Glance

| Workflow | Trigger | Does |
| --- | --- | --- |
| `ci.yml` | Every PR | Lint (Ruff/ESLint), type check (mypy/tsc), migration lint, pytest w/ coverage gate, Docker smoke test, TruffleHog secret scan, `uv audit` / `npm audit`, dependency-review CVE gate |

If a PR fails the dependency-review step, it's usually a newly introduced CVE — check the CI log for the specific advisory before overriding anything.

---

## 8. Where to Go Next

- [Confluence](https://cs598spring2026.atlassian.net/wiki/spaces/SD/overview)
- [Jira](https://cs598spring2026.atlassian.net/jira/software/projects/KAN/list?jql=project%20%3D%20KAN%20AND%20assignee%20%3D%20712020%3Ae9f3c63f-5d5c-4500-adcb-179320eb85ef%20AND%20statusCategory%20in%20(%22To%20Do%22%2C%20%22In%20Progress%22%2C%20New%2C%20Complete)%20ORDER%20BY%20updated%20DESC)
- [Project README](./README.md) — quick-start summary and architecture overview
- [Backend README](./backend/README.md) — Detailed backend document
- [Frontend README](./frontend/README.md) — Detailed backend document

If something in this guide is stale, it's a docs bug — open a Jira bug issue and it'll get fixed like any other bug.

---

## 9. Getting Help

- Post questions as GitHub Issues (tag appropriately) so answers stay discoverable for the whole team.

# AI Usage & Verification Log

**Project Name:** QuestLog
**Team Name:** The Meeples
**Team Lead:** N/A

---

## Overview & AI Policy Compliance Statement

This repository utilizes Generative AI tools (e.g., ChatGPT, Claude, GitHub Copilot) in compliance with course AI guidelines. AI tools are used for code scaffolding, SQL migration generation, test suite generation, and documentation drafting. All AI-generated code is reviewed, refactored for Object-Oriented Programming (OOP) design standards, and verified via automated test suites prior to PR approval.

---

## Entry Template (copy for new entries)

## Entry N: [Prototype #] — [Short Feature Description]

* **Date:**
* **Team Member:** (`@handle`)
* **Tool Used:** [Tool]
* **Associated Git Issue:** Closes `#`
* **Associated Feature Branch:** `feature/...`

### Exact Prompt Submitted:

> "..."

### AI Output Summary & Code Generated:


### Human Review, Refactoring & Modifications Made:

*
*

### Verification & Testing Method:

*
*

---

## Audit Certification

I certify as Team Lead that all entries above accurately represent AI usage within this project phase, all prompts have been recorded, and all code has been validated by human review and automated testing.

**Team Lead Signature:** *[Team Lead]* — **Date:** [Date]

---
## Entry 42000: Example

* **Date:** September 2, 2026
* **Team Member:** Jane Doe (`@janedoe`)
* **Tool Used:** Claude 3.5 Sonnet
* **Associated Git Issue:** Closes `#12` (Setup Initial PostgreSQL Schema)
* **Associated Feature Branch:** `feature/database-migrations`

### Exact Prompt Submitted:

> "Write a Knex.js SQL migration file for a PostgreSQL database. I need a 'users' table with columns for id (uuid primary key), email (unique), password_hash, role (enum: admin, user), created_at, updated_at, and a soft-delete column 'deleted_at'. Also include a corresponding down migration script to drop the table and enum type cleanly."

### AI Output Summary & Code Generated:

AI generated a Knex migration file containing `exports.up` and `exports.down` functions with table schema creation and drop statements.

### Human Review, Refactoring & Modifications Made:

* **Security & Formatting:** Added explicit check constraints on `email` format.
* **Data Safety:** Modified `deleted_at` column to default to `NULL` and added a database index on `deleted_at` to optimize soft-delete queries.
* **OOP Encapsulation:** Wrapped query builders inside a `UserRepository` data access class.

### Verification & Testing Method:

* Executed `npx knex migrate:latest` -> Table created successfully.
* Executed `npx knex migrate:rollback` -> Rollback executed without residual enum type locks.
* Passing automated unit tests logged in CI build run `#45`.

---

## Entry 1: Prototype 1 — Jira ↔ GitHub Issues Integration Strategy
* **Date:** August 8, 2026
* **Team Member:** Jennifer Isobe (`@jisobe`)
* **Tool Used:** Claude Sonnet 5
* **Associated Git Issue:** Closes N/A
* **Associated Feature Branch:** N/A

### Exact Prompt Submitted:
> "How can I link jira items (epics, stories, tasks, bugs, etc) to GitHub issues. How can i transfer jira items to GitHub issues? Can I create a jira automation?"

### AI Output Summary & Code Generated:
AI outlined three distinct integration strategies for connecting Jira (Epic/Story-level planning) to GitHub Issues (granular task/bug tracking, required by course rubric):
1. **GitHub for Jira app** — links existing items via issue-key references in branch names, commits, and PR titles (no data duplication, native GitHub Marketplace app).
2. **One-time migration script** — Python script using Jira REST API (`/rest/api/3/search`) and GitHub REST API (`/repos/{owner}/{repo}/issues`) to bulk-copy existing Jira backlog items into GitHub Issues, with field mapping (Jira issue type → GitHub label) and back-reference links.
3. **Jira Automation rule** — no-code "Send web request" automation action that POSTs to the GitHub Issues API on issue creation, using Jira smart values (`{{issue.summary}}`, `{{issue.description}}`, `{{issue.key}}`) for field mapping, with an optional second action to write the resulting GitHub issue number back into a Jira custom field.

No code was directly generated for the repository; output was architectural/process guidance and a proposed automation rule configuration (trigger, condition, web request payload).

### Human Review, Refactoring & Modifications Made:
* **Decision:** Evaluated the three approaches for one-way vs. two-way sync trade-offs, GitHub PAT storage/rotation on the free Jira Automation tier, and backfill limitations (automation rules don't retroactively sync existing backlog items).
* **Chosen approach:** Utilize Jira automation
* **Modifications:** Created a jira automation to create a GitHub issue when a Jira items is move into TODO from backlog.

### Verification & Testing Method:
* Moved a Jira issue from backlog to TODO and verified associated Github issue was created

## Entry 2: Prototype 1 — CI Readiness Check False Failure (JSON Format Mismatch)
* **Date:** September 9, 2026
* **Team Member:** Jennifer Isobe `@jisobe`
* **Tool Used:** Claude Sonnet 5
* **Associated Git Issue:** Closes `#16` Update docker and backend to use uv and standardize commit messages
* **Associated Feature Branch:** `jisobe_docker`

### Exact Prompt Submitted:
> "getting this ci failure [pasted GitHub Actions log showing `/ready/` returning `{"status":"ok","checks":{"database":"ok","redis":"ok"}}` but the workflow step still reporting 'Backend reported unhealthy dependencies' and exiting 1]"

### AI Output Summary & Code Generated:
Claude diagnosed that the `/ready/` endpoint was returning valid, healthy JSON, but the CI step's `grep -q '"status": "ok"'` check expected a space after the colon while Django's JSON response serializer produced no space (`"status":"ok"`), causing the grep to never match. Claude recommended replacing the fragile string-match grep with `jq -e '.status == "ok"'` to parse the JSON structurally instead of matching exact text formatting.

### Human Review, Refactoring & Modifications Made:
* Replaced the `grep -q '"status": "ok"'` line in `.github/workflows/ci.yml` with `jq -e '.status == "ok"' > /dev/null`.
* Verified `jq` is available by default on GitHub-hosted `ubuntu-latest` runners (no additional install step needed).

### Verification & Testing Method:
* Re-ran the CI job; CI continued to fail.

---

## Entry 3: Prototype 1 — Frontend Standalone Container Fails to Accept Connections (Turbopack Build Regression)
* **Date:** September 9, 2026
* **Team Member:** `@jisobe`
* **Tool Used:** Claude Sonnet 5 (with web search)
* **Associated Git Issue:** Closes `#16` Update docker and backend to use uv and standardize commit messages
* **Associated Feature Branch:** `jisobe_docker`

### Exact Prompt Submitted:
> "Waiting for frontend... (15/30) ... Frontend did not respond in time [pasted CI logs showing the frontend container running, port correctly published, but `wget` connection refused even from inside the container, alongside the build log showing `▲ Next.js 16.2.3 (Turbopack)` and `✓ Ready in 0ms`]"

### AI Output Summary & Code Generated:
Claude ran diagnostic steps (internal `wget`, `docker inspect`, `/proc/net/tcp` socket inspection) to isolate whether the failure was a Docker networking issue or an application-level fault, ultimately determining no process was actually listening on port 3000 despite the "Ready" log line. Claude used web search to confirm this matched a known, currently-open upstream issue in `vercel/next.js` where Turbopack-built `output: standalone` bundles can report ready without a functioning listener and can omit runtime dependencies from `.next/standalone/node_modules`. Claude noted that Next.js 16 defaults `next build` to Turbopack even without an explicit flag, and recommended forcing Webpack for the production standalone build via `next build --webpack`.

### Human Review, Refactoring & Modifications Made:
* Changed the `builder` stage of `frontend/Dockerfile` from `RUN npm run build` to `RUN npx next build --webpack`, scoping the change to the Docker production build only (local `npm run dev` continues to use Turbopack, which is unaffected by this issue).
* Verified the resulting build log no longer showed the `(Turbopack)` suffix.
* Updated the CI wait step to use `127.0.0.1` and `0.0.0.0` instead of `localhost` (to avoid IPv6-resolution ambiguity on GitHub-hosted runners) and extended the retry window, after confirming via `/proc/net/tcp` that the corrected build did produce a real `LISTEN` socket on port 3000.

### Verification & Testing Method:
* Re-ran the `frontend-standalone-build` CI job and Job continued to fail.

---

## Entry 4: Prototype 1 — Developer Onboarding Guide
* **Date:** September 10, 2026
* **Team Member:** Jennifer Isobe (`@jisobe`)
* **Tool Used:** Claude Sonnet 5
* **Associated Git Issue:** Closes `#16` Update docker and backend to use uv and standardize commit messages
* **Associated Feature Branch:** `jisobe_docker`

### Exact Prompt Submitted:
> "please create a developer onboarding guide using the provided readmes. Add link(s) to confluence as most of our architecture/standards documents are there"

### AI Output Summary & Code Generated:
AI generated `DEVELOPER_ONBOARDING.md`, a full onboarding guide covering: prerequisites, first-time clone/setup steps (`npm install` at root for Husky hooks, `docker compose up`), repository folder structure with annotations, OOP design pattern conventions for both Django/DRF (thin views, service/repository classes, typed serializers, soft-delete pattern) and Next.js/TypeScript, environment variable reference matching the project's discrete `DATABASE_*` / `DJANGO_SECRET_KEY` shape, branching/commit conventions, a CI/CD pipeline summary table, and placeholder links out to the team's Confluence space for architecture/sprint/API docs.

### Human Review, Refactoring & Modifications Made:
* **Confluence Links:** Placeholder `[LINK]` markers left in Section 8 — need to be replaced with actual Confluence space URLs before submission.
* **Accuracy check:** AI flagged that `docker-compose.yml`'s `frontend` service is currently commented out and documented the manual `npm run dev` workaround instead of the (currently nonfunctional) single-command path for the frontend.
* **Config hygiene flag:** AI noted `db`, `redis`, and `backend` services in `docker-compose.yml` each declare both `env_file` and a redundant `environment:` block, which conflicts with the team's own "env_file only" convention — logged as a follow-up cleanup item, not fixed in this pass.
* Updated README information to match current setup

### Verification & Testing Method:
* Cross-referenced generated folder structure and env var names against actual `docker-compose.yml` and project conventions on file.

---

## Entry 5: Prototype 2 — Catalog API Serializer Split

* **Date:** September 24, 2026
* **Team Member:** Brandon Nguyen (`@Meynok`)
* **Tool Used:** Gemini 1.5 Pro
* **Associated Git Issue:** Closes `#67`
* **Associated Feature Branch:** `feat/catalog-get-endpoints`

### Exact Prompt Submitted:

> "i need to show my `BoardGame` model via api endpoints. how would you recommend configuring django REST Framework to include all the nested metadata when querying a single game by id"

### AI Output Summary & Code Generated:

AI recommended creating two separate serializers and overriding `get_serializer_class` in a `ModelViewSet` or `GenericViewSet`. It generated boilerplate for a list serializer and a detail serializer, mapping the HTTP actions (`list` vs `retrieve`) to the appropriate class.

### Human Review, Refactoring & Modifications Made:

* Created `BoardGameListSerializer` mapping only core fields like `bgg_id` and `average_rating`.
* Created `BoardGameDetailSerializer` mapping full arrays for categories, mechanics, and other attributes using a nested `BGGAttributeSerializer`.
* Implemented `BoardGameViewSet` in `views.py` routing to the list serializer on `self.action == "list"`.

### Verification & Testing Method:

* Requested `/api/v1/games/` and confirmed nested M2M arrays were omitted.
* Requested `/api/v1/games/13/` and confirmed full payload returned.

---

## Entry 6: Prototype 2 — Recommendation Engine (Phase I)

* **Date:** October 3, 2026
* **Team Member:** Jennifer Isobe (`@Jisobe`)
* **Tool Used:** Claude Code (Claude Opus 5.5)
* **Associated Git Issue:** Closes `#76`
* **Associated Feature Branch:** `feature/KAN-251-Add-basic-recommendations-based-on-overall-rating-from-BGG`

### Exact Prompt Submitted:

> "I am working on implementing a basic recommender system. I am planning to use context filtering with cosine similarity, what would be the best tools to use for this implementation? Should another app be created should additional models be created"

### AI Output Summary & Code Generated:

Suggesting adding a `recommendations` Django app. Phase I (content-based filtering) recommended tools include pandas and scikit-learn: TF-IDF weighted category, mechanic, and designer vectors and scaled player count, play time, and complexity, ranked by cosine similarity. Provided example code for TF-IDF vector weights and basic content filtering setup using pandas and scikit.

### Human Review, Refactoring & Modifications Made:

* Review suggestions to determine if they fit the project architecture and needs
* Review provided code to understand how implementation should work for QuestLog

### Verification & Testing Method:

* Researched cosine similarity and TF-IDF weighted vectors to better understand thier implementation
* Created a recommendations app and updated models with basic views and serializers

## Entry 7: Prototype 2 — Recommendation Engine (Phase I)

* **Date:** October 3, 2026
* **Team Member:** Jennifer Isobe (`@Jisobe`)
* **Tool Used:** Claude Code (Claude Opus 5.5)
* **Associated Git Issue:** Closes `#76`
* **Associated Feature Branch:** `feature/KAN-251-Add-basic-recommendations-based-on-overall-rating-from-BGG`

### Exact Prompt Submitted:

> "I am also working on implementing filters for the recommendations. I think it would be easiest to work on implemeting this early rather than waitng unti later, does this make sense? How can the phase I recommendations be incorporated with the filters." **Provided notes from last semester containing ideas and plans for implementation**

### AI Output Summary & Code Generated:

Suggested creating files for filter metrics, updates for opt-in consent with a basic fallback, an optional onboarding profile for new users, recommendation feedback, Redis caching, an `average_weight` (complexity) field on `BoardGame` based on provided notes.

### Human Review, Refactoring & Modifications Made:

* Review suggestions to determine if they fit the project architecture and needs
* Created new files to add the filtering criteria
* Updated recommendation models, views, and serializers to use filtering criteria

### Verification & Testing Method:

* Added tests for recommendations and updated filtering and opt-in

## Entry 8: Prototype 2 — Recommendation Engine (Phase I)

* **Date:** October 4, 2026
* **Team Member:** Jennifer Isobe (`@Jisobe`)
* **Tool Used:** Claude Code (Claude Opus 5.5)
* **Associated Git Issue:** Closes `#76`
* **Associated Feature Branch:** `feature/KAN-251-Add-basic-recommendations-based-on-overall-rating-from-BGG`

### Exact Prompt Submitted:

> "How does getting the boardgame information for the recommendations work? how do I format the data in a way tha tis usable by the context filter and later phases based on previously provided notes"

### AI Output Summary & Code Generated:

Outlined implementation of data retrieval pipeline and implementation of data.py to create pandas dataframes from queried boardgame data.

### Human Review, Refactoring & Modifications Made:

* Walked through data.py line by line to understand the implementation and its use.
* Updated functions and variable to match existing backend architecture

### Verification & Testing Method:

* Added tests to the test.py file in recommendations.

---

## Entry 9: Prototype 2 — Security audit

* **Date:** October 8, 2026
* **Team Member:** Jennifer Isobe (`@jisobe`)
* **Tool Used:** Claude Sonnet 5
* **Associated Git Issue:** Closes 101
* **Associated Feature Branch:** feature/prototype-2-security-check

### Exact Prompt Submitted:

> "Perform a complete audit of the repository using the OWASP Top 10 as reference, suggest mitigatino steps"

### AI Output Summary & Code Generated:

Performed a complete security audit for the entire code repository for each of the OWASP Top 10 items. Create docs/SECURITY_AUDIT.md with status, controls, open issues and mitigations for each item.

### Human Review, Refactoring & Modifications Made:

* Review the full security audit document to understand identified issues
* Confirmed tested OWASP items against the official list
* Review code that was identified as problematic
* Added some changes to address some issues

### Verification & Testing Method:

* Reran test locally and through the CI pipeline

---

## Entry 10: Prototype 2 — Architecture & UML Diagrams

* **Date:** October 8, 2026
* **Team Member:** Jennifer Isobe (`@jisobe`)
* **Tool Used:** Claude Code (Claude Opus 5.5)
* **Associated Git Issue:** Closes `#`
* **Associated Feature Branch:** `feature/prototype-2-security-check`

### Exact Prompt Submitted:

> "Create visualizations for the front and backend architectures, dataflows and pipelines, etc. then add an entry to the AI_USAGE_LOG file"

### AI Output Summary & Code Generated:

AI read the models, migrations, URL routes, views, permissions, mixins, recommendation services, frontend pages, `docker-compose.yml` and `ci.yml`, then created `docs/ARCHITECTURE.md` with 13 Mermaid diagrams that GitHub renders directly from the Markdown:

1. System context (browser → Next.js → Django → PostgreSQL / Redis / BoardGameGeek / SMTP), with a table of Redis database uses
2. Docker Compose runtime (containers, ports, health-check start order, volumes)
3. Backend module structure (Django apps and their import dependencies)
4. UML class diagram of the domain models (fields, methods, inheritance, multiplicities)
5. UML class diagram of the API layer (viewsets, permission classes, mixins, throttles, recommendation services)
6. Two entity relationship diagrams (accounts/roles/social; catalog/tracking/recommendations)
7. Request and authorization pipeline, with the status code returned at each check
8. Sequence diagrams for sign up → email verification → login → MFA setup, game lookup with BGG fallback, and library add / soft delete
9. Activity diagram of the recommendation engine (cache, consent check, fallback, invalidation)
10. CI/CD pipeline jobs and dependencies

AI also added a small overview diagram and links to `docs/ARCHITECTURE.md` in the `README.md` Architecture Overview and Further Documentation sections.

While checking the diagrams against the code, AI corrected its first draft of the login sequence diagram: the frontend sends users to `/login?setup=mfa` after email verification, and the login page does not yet submit MFA codes to `/auth/2fa/authenticate`. The diagram shows this gap instead of an MFA login step that does not exist. AI also flagged that the library page does not call the API yet, a stray `backend/core/tests 2.py` file, and two places where `docs/SECURITY_AUDIT.md` no longer matched the merged code.

### Human Review, Refactoring & Modifications Made:

* Reviewed each diagram against the current code base and project design
* Removed the stray `backend/core/tests 2.py` duplicate file flagged during the review

### Verification & Testing Method:

* AI rendered every diagram with the Mermaid CLI (`@mermaid-js/mermaid-cli`), the same renderer GitHub uses. The first run failed on a semicolon in the login sequence diagram, which Mermaid treats as a statement separator. After that fix, all 13 diagrams rendered without errors.
* AI converted the system context, domain class and request pipeline diagrams to images and checked them for readability

---

## Entry 11: Prototype 2 — Fix frontend CI failures from Dependabot major-version bumps

* **Date:** October 9, 2026
* **Team Member:** Brandon Nguyen (`@Meynok`)
* **Tool Used:** Gemini 1.5 Pro
* **Associated Git Issue:** Closes `#122`
* **Associated Feature Branch:** `fix/frontend-ci-dependency-majors`

### Exact Prompt Submitted:

> "fix ci error"

### AI Output Summary & Code Generated:

AI ran every CI step locally against `main` to find which ones were failing. The backend job passed. The frontend job failed in ESLint, Jest and `next build`. AI traced each failure to one of three Dependabot pull requests merged the same day that each moved a tool up a major version:

1. **TypeScript 5.9.3 → 7.0.2:** `typescript-eslint` refuses to run on TypeScript 7, and `ts-node` (which Jest uses to load `jest.config.ts`) crashes on it. This broke ESLint and Jest.
2. **ESLint 9.39.4 → 10.12.0:** ESLint 10 removed `context.getFilename()`, which the `eslint-plugin-react` bundled with `eslint-config-next` still calls. This crashed ESLint.
3. **Tailwind CSS 3.4.19 → 4.3.3:** Tailwind 4 moved its PostCSS plugin to a separate `@tailwindcss/postcss` package and replaced the `@tailwind` directives. The frontend still uses the Tailwind 3 setup, so `next build` failed.

Changes made:

* `frontend/package.json`: rolled `typescript` back to `^5`, `eslint` to `^9` and `tailwindcss` to `^3.4.19`, the exact ranges from before the bumps.
* `frontend/package-lock.json`: regenerated with npm. AI compared it package by package against `main` to confirm that only those three packages, their own sub-dependencies, and two small patch updates (`hasown`, `is-core-module`) changed.
* `.github/dependabot.yml`: added `ignore` rules for major updates of those three packages only, each with a comment explaining why, so Dependabot does not reopen the same upgrades. Minor and patch updates still arrive.

AI also found that a local Prettier failure was a false alarm caused by Windows line endings (CRLF) in the local checkout. The files are stored with LF in Git, which is what CI sees.

### Human Review, Refactoring & Modifications Made:

* Reviewed the changes, made sure they were safe.

### Verification & Testing Method:

* AI ran each frontend CI step the same way CI runs it: `npm ci`, `npm run lint`, `npm run typecheck`, the Prettier format check (with LF line endings, as CI sees them), `npm run test:coverage` (2 suites, 9 tests) and `npm run build`. All passed, and `npm audit --omit=dev` found 0 vulnerabilities.
* AI ran the backend CI steps (Ruff lint and format, complexity caps, mypy, migration drift and linting, Django system check, pytest with the 60% coverage gate). All passed: 158 tests, 92.5% coverage.
* AI parsed the edited `dependabot.yml` to confirm it is valid YAML and that the three ignore rules load correctly.

---

## Entry 12: Prototype 3 — Recommendation Engine (Phases II & III)

* **Date:** November 1, 2026
* **Team Member:** Jennifer Isobe (`@Jisobe`)
* **Tool Used:** Claude Code (Claude Opus 5.5)
* **Associated Git Issue:** Closes `#144`
* **Associated Feature Branch:** `feature/advanced-recommender`

### Exact Prompt Submitted:

> "Using the following outline, provide an outline for the implementation of phase II and III of the recommendation system. Include reasoning behind choices and alternatives if applicible. provide an AI-USAGE_LOG entry." **Provided the recommendation engine outline: recommendation filters, considerations (data sources, new users, opt-in, basic fallback, caching, feedback), phases I–IV, and the planned tech stack**

### AI Output Summary & Code Generated:

AI proved:

**Phase II: collaborative filtering** (`recommendations/collaborative.py`, Surprise)

* A biased SVD matrix factorization trained on the interaction scores (ratings, likes/dislikes, plays, ownership) of opted-in users only. It trains once there are at least 3 opted-in users and 10 interactions.
* Personalized rankings now blend content and collaborative scores. The collaborative share grows with the user's activity, up to 60%. New users, and users the model has not seen yet, still get Phase I recommendations.
* New `players_like_you` strategy (personal data, opt-in required) that uses collaborative filtering alone.
* The cached model is keyed on the set of opted-in users, so it retrains without a user as soon as they opt out.

**Phase III: advanced recommenders** (`recommendations/embeddings.py`, pgvector)

* New `GameEmbedding` model. Each game gets a 64-dimension hybrid embedding built from its content features and its collaborative factors, reduced with truncated SVD and stored behind an HNSW cosine index.
* `for_you` now works in two stages: it retrieves the 200 unseen games nearest the user's embedding, then ranks them by hybrid taste score plus embedding similarity. User embeddings are computed per request and never stored.
* New `similar_games?game_id=` strategy (basic, no personal data) that returns a game's nearest neighbors, falling back to content similarity until embeddings have been built.
* `manage.py train_recommender` now rebuilds the content model, the collaborative model and the stored embeddings (`--skip-embeddings` rebuilds only the cached models).

### Human Review, Refactoring & Modifications Made:

* Reviewed provided outlines for each outline/plan to check for usability and correctness
* Made updated to the backend recommendations in accordance with the plan and integrated changes into existing recommendation code

### Verification & Testing Method:

* AI added 15 tests covering collaborative model training, cold-start users and games, opt-out removal from the cached model, embedding size and normalization, embedding rebuilds, nearest-neighbor search, the `similar_games` and `players_like_you` strategies, the content + collaborative blend in `for_you`, `for_you` candidate retrieval from the embedding index, and `game_id` validation.
* AI ran the full backend suite against temporary `pgvector/pgvector:pg17` and Redis containers: 173 tests passed, with 93% coverage for the recommendations app.
* AI ran `migrate` on a fresh database, `makemigrations --check` (no drift), `lintmigrations` (one warning: the HNSW index is created inside the migration's transaction, on a new, empty table), `train_recommender`, Ruff lint and format, and mypy. All passed.

---

## Entry 13: Prototype 3 — Recommendation Engine (Phase IV), Structured Logging & Monitoring

* **Date:** November 1, 2026
* **Team Member:** Jennifer Isobe (`@Jisobe`)
* **Tool Used:** Claude Code (Claude Opus 5.5)
* **Associated Git Issue:** Closes `#145`
* **Associated Feature Branch:** `feature/add-logging-and-monitoring`

### Exact Prompt Submitted:

> "Make updates for phase IV and to add Structured JSON logging (timestamp, log level, request ID, user ID) and monitoring across backend services"

### AI Output Summary & Code Generated:

**Structured JSON logging** (`core/structured_logging.py`, `core/middleware.py`)

* Every backend log line is now a single JSON object with `timestamp` (UTC), `level`, `logger`, `message`, `request_id` and `user_id`, plus any fields passed with `extra=`.
* New `RequestContextMiddleware` gives each request an ID. It reuses a well-formed incoming `X-Request-ID` header, otherwise generates one, and returns it in the response. The request ID and signed-in user's ID are attached to every log line written during the request. It also writes one access-log line per request (INFO / WARNING / ERROR by status) and skips health checks and metrics scrapes unless they fail.
* Added a `LOGGING` configuration to `settings.py` and connected the `LOGLEVEL` variable, which was documented in `.env.example` but unused. `LOG_FORMAT=text` gives readable lines for local debugging. Django's own 4xx log lines were turned off because they duplicated the access log and had no request ID; unhandled 500 errors still keep their request ID and stack trace.
* New `core/signals.py` logs security events (sign-in, failed sign-in, sign-out, sign-up, password change/reset, MFA authenticator added/removed/failed) by user ID only. Failed sign-ins never log the email that was tried. This addresses the A09 recommendation in `docs/SECURITY_AUDIT.md`.
* Removed BGG usernames from the BGG play-sync error messages, since every log line now carries the user ID.

**Monitoring across backend services** (`core/metrics.py`, `prometheus-client`)

* New `GET /metrics/` endpoint serving Prometheus metrics to callers with a `METRICS_TOKEN` bearer token (404 when the token is unset).
* Metrics for HTTP requests and latency (by URL pattern), PostgreSQL/Redis readiness, BoardGameGeek API calls by outcome, security events, recommendation requests (fallbacks and cache hits), recommendation compute time and model build times.
* Production gunicorn now uses `config/gunicorn.conf.py` and `PROMETHEUS_MULTIPROC_DIR` so metrics are combined across workers. `entrypoint.sh` clears stale metric files on startup.
* Optional Prometheus container in `docker-compose.yml` (`docker compose --profile monitoring up`) with `monitoring/prometheus.yml`.

**Phase IV: recommender monitoring** (`recommendations/evaluation.py`, `recommendations/experiments.py`)

* Offline evaluation: holds out 20% of opted-in users' interactions with a fixed split and reports RMSE, MAE, precision@10 and recall@10 for the collaborative model.
* Online feedback: like and dislike counts and like rate per strategy, using the strategy recorded on each piece of feedback.
* Experiment trackers selected with `RECOMMENDER_TRACKERS`: `log` (structured log line, the default), `mlflow` and `wandb`. W&B defaults to offline mode. A tracker that is missing or fails is logged and skipped so model rebuilds are never blocked.
* `train_recommender` now times each build, runs the evaluation (`--skip-evaluation` to skip it), and reports the run with the model parameters. New `recommendation_report --days N` command prints and reports the feedback summary.
* Added `prometheus-client` as a dependency, and `mlflow` and `wandb` as an optional `monitoring` extra so the Docker image stays small.

**Docs and configuration:** updated `backend/README.md` (new Logging & Monitoring section and Phase IV), `docs/ARCHITECTURE.md`, `ONBOARDING.md`, `.env.example` and `.gitignore` (local MLflow and W&B output).

### Human Review, Refactoring & Modifications Made:

* Review the ai produced code for backend logging and monitoring via prometheus
* Tested the prometheus monitoring endpoint and identified and issue with .env file variable keeping monitoring from executing
* Review the added monitoring for the recommender system

### Verification & Testing Method:

* AI added 27 tests covering the JSON formatter, request ID generation and reuse (including rejecting malformed IDs), user ID on log records, request context being cleared after each request, 500 errors keeping their request ID, metrics endpoint token checks, external API and request counters, security event logging without email addresses, offline evaluation, feedback summaries, each tracker (MLflow and W&B replaced with fakes), tracker failure handling, both management commands, and recommendation serving metrics.
* AI ran the full backend suite against temporary `pgvector/pgvector:pg17` and Redis containers: 200 tests passed. Ruff lint and format, mypy, the complexipy complexity check, `makemigrations --check` and `manage.py check` all passed. AI refactored one evaluation helper that exceeded the complexity limit.
* AI ran `train_recommender` and `recommendation_report` with the real MLflow and W&B libraries, using a local SQLite MLflow store and W&B offline mode. All three trackers recorded both runs. This found that `mlflow-skinny` cannot use SQLite stores, so AI switched the optional dependency to full `mlflow`.
* AI started the development server and confirmed the JSON access log lines, the `X-Request-ID` response header, and the `/metrics/` token check. This found Django's duplicate 4xx log lines without a request ID, which AI then turned off.
* AI validated `docker-compose.yml` with the monitoring profile using `docker compose config`.
* No external APIs (BoardGameGeek, MLflow servers, Weights & Biases) were called.

## Entry 14: [Prototype 3] — [Fixing Errors Thrown by E2E and Accesibility Pipeline]

* **Date:** : November 3rd
* **Team Member:** Sydney Epke (`@vortex278`)
* **Tool Used:** Github Copilot
* **Associated Git Issue:** Closes `#`
* **Associated Feature Branch:** `chore/fix_e2e_and_accessibility_errors`

### Exact Prompt Submitted:

> "can you look at PR #170 and help me fix the failing checks?"

### AI Output Summary & Code Generated:

The AI found a .env error and replaced the reference to the original hardcoded .env to an example .env file in docker.ts and docker-compose.yml

### Human Review, Refactoring & Modifications Made:

* I checked to make sure this was a good change and that the example .env did not have any secrets in it
* I ran the commands to run the checks locally
* I pushed the code and ran the checks in GitHub

### Verification & Testing Method:

* Just running the checks locally and then running it in GitHub after pushing again

---

## Audit Certification

I certify as Team Lead that all entries above accurately represent AI usage within this project phase, all prompts have been recorded, and all code has been validated by human review and automated testing.

**Sydney Epke:** *[Testing Lead]* — **Date:** [11/03/26]

---

## Entry 15: Prototype 3 — Merge Celery Background Tasks into the BGG Refresh Branch

* **Date:** November 3, 2026
* **Team Member:** Brandon Nguyen (`@Meynok`)
* **Tool Used:** Claude Code (Claude Opus 5.5)
* **Associated Git Issue:** Closes `#175`
* **Associated Feature Branch:** `feat/bgg-refresh` (draft PR #176)
* **Commits:** `91dce56` (merge of `feature/celery`), `ba19fbf` (`fix: retry background play sync only for retryable bgg errors`)

### Exact Prompt Submitted:

> "we have conflicts in PR #163 and #169. please resolve these conflicts into this branch"

### AI Output Summary & Code Generated:

**`91dce56` — Merge `feature/celery` (#163) into `feat/bgg-refresh`**

* Merged Jennifer's Celery branch (worker, beat, Flower, background BGG play import) into the branch that already contained the BGG client from `feat/bgg-catalog` (#169), so the catalog refresh work could build on both before either PR is merged.
* Resolved the one conflict, in `tracking/utils.py`: kept the `import_bgg_plays` / `fetch_bgg_plays` split and message constants from `feature/celery`, and used the BGG client's `BoardGameGeekUnavailableError` and `BoardGameGeekMalformedResponseError` in place of the `requests` and `ElementTree` errors the BGG client replaced.
* Updated the `import_bgg_plays` docstring to list the client errors it now raises.
* Removed an unused `Profile` import left in `tracking/views.py` (also present on `feature/celery`, where it fails the backend lint).

**`ba19fbf` — Retry background play sync only for retryable BGG errors**

* Found a problem the merge did not show as a conflict: `sync_bgg_plays` in `tracking/tasks.py` caught `requests.RequestException` and read `exception.response.status_code` to decide whether to retry. After the merge the play import raises the BGG client's errors instead, so every BGG failure skipped those `except` blocks and the task was marked FAILED without retrying. The task tests did not catch this because they mock `import_bgg_plays` and raise `requests` errors themselves.
* Added `is_retryable` and `status_code` to `BoardGameGeekUnavailableError` in `catalog/bgg_client.py`. Timeouts, connection failures, rate limiting (429) and server errors (5xx) are retryable; a request BGG rejects itself (for example, a 404 for an unknown username) is not.
* Changed `sync_bgg_plays` to catch the two client errors and retry only when `is_retryable` is True, and removed `_is_retryable` and `RETRYABLE_HTTP_STATUSES`.
* Updated the task tests in `tracking/test_tasks.py` to raise the client's errors, and added a test that unreadable BGG XML fails the sync without retrying.

### Human Review, Refactoring & Modifications Made:

* Reviewed the merge and changes made. Determined that they were the right direction to go in

### Verification & Testing Method:

* AI ran the full backend suite against a temporary `pgvector/pgvector:pg17` container: 299 tests passed, including Jennifer's Celery task tests and the new unreadable-XML test.
* AI ran Ruff lint and format, mypy, `uv lock --check` (the merged lockfile resolves), `makemigrations --check` (no drift) and `lintmigrations` (no erroneous migrations). All passed.
* No external APIs (BoardGameGeek) were called; the tests mock the BGG client.

---

## Audit Certification

I certify as Team Lead that all entries above accurately represent AI usage within this project phase, all prompts have been recorded, and all code has been validated by human review and automated testing.

**Sydney Epke:** *[Testing Lead]* — **Date:** [11/03/26]
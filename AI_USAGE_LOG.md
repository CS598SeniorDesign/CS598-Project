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
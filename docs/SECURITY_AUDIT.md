# QuestLog Security Audit — Prototype 2 (OWASP Top 10)

| | |
| :--- | :--- |
| **Audit date** | October 8, 2026 |
| **Baseline** | `main` at `ceaa260` plus the `feature/prototype-2-security-check` changes listed below |
| **Scope** | Django backend (`backend/`), Next.js frontend (`frontend/`), Docker Compose stack, GitHub Actions pipeline |
| **Standard** | [OWASP Top 10:2025](https://owasp.org/Top10/) |
| **Method** | Manual code and configuration review, plus automated tooling: TruffleHog (secrets), `uv audit` / `npm audit` / GitHub Dependency Review (dependencies), Ruff + complexipy + ESLint SonarJS (static analysis) |

---

## Summary

| # | Category | Status | Key controls in place |
| :-- | :--- | :---: | :--- |
| A01 | Broken Access Control | ✅ Mitigated | DRF defaults to `IsAuthenticated`; catalog API is read-only; admin disabled unless `ADMIN_ENABLED`; disabled features return 404 |
| A02 | Security Misconfiguration | ⚠️ Partial | `DEBUG=False` default, HSTS, secure/HttpOnly cookies, `X-Frame-Options: DENY`, `nosniff` |
| A03 | Software Supply Chain Failures | ⚠️ Partial | Dependency Review blocks new CVEs on PRs; `uv audit` + `npm audit` gate |
| A04 | Cryptographic Failures | ✅ Mitigated | Argon2 password hashing; secrets only via env; HTTPS redirect + HSTS (1 year, preload) in production |
| A05 | Injection | ⚠️ Partial | Django ORM only (no raw SQL with input); `defusedxml` for all BGG XML; React escapes output; BGG query-string injection via username in URL |
| A06 | Insecure Design | ⚠️ Partial | Rate limiting (anon 60/min, user 300/min, BGG sync 3/min); BGG username uniqueness prevents importing other users' plays; open items on catalog fetch |
| A07 | Authentication Failures | ✅ Mitigated | django-allauth: mandatory email verification, enumeration protection, built-in login rate limits, MFA (TOTP, recovery codes, WebAuthn/passkeys), password validators |
| A08 | Software or Data Integrity Failures | ⚠️ Partial | Locked dependency files (`uv.lock`, `package-lock.json`, `--locked` / `npm ci`); CSRF enforced for session auth; Actions not pinned to SHAs |
| A09 | Security Logging and Alerting Failures | ❌ Gap | Warnings logged for BGG failures only; no auth/audit logging or alerting yet (planned for Prototype 3 structured logging) |
| A10 | Mishandling of Exceptional Conditions | ✅ Mitigated | BGG failures caught and return generic messages; play sync is atomic per page and rolls back on error; health probes fail closed (503) |

---

## Findings by Category

### A01 — Broken Access Control

**Controls**

- `REST_FRAMEWORK.DEFAULT_PERMISSION_CLASSES = IsAuthenticated` ([settings.py](../backend/config/settings.py)), so new
  endpoints are private unless they opt out. Only `/health/` and `/ready/` use `AllowAny`.
- `BoardGameViewSet` exposes list/retrieve only; serializers raise on create/update.
- Django admin is only routed when `ADMIN_ENABLED=True` (defaults to the value of `DEBUG`).
- Feature flags (`core.feature_flags.FeatureFlagPermission`) return 404 for disabled endpoints, even to anonymous
  users, so incomplete features are not discoverable.

### A02 — Security Misconfiguration

**Controls**

- `DEBUG` defaults to `False`; `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` come from the environment.
- `SECURE_HSTS_SECONDS = 31536000` with subdomains + preload; `SECURE_SSL_REDIRECT` toggled per environment;
  `SECURE_PROXY_SSL_HEADER` set when not in debug.
- Cookies: `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` in production, `HttpOnly` session cookie, `SameSite=Lax`.
- The production backend image runs as the unprivileged `appuser`; the frontend image runs as `nextjs`.
- An empty `DJANGO_SECRET_KEY` makes Django raise `ImproperlyConfigured` instead of running with a blank key.

**Open items**

| Severity | Item | Recommendation |
| :---: | :--- | :--- |
| High | `/ready/` is public and return raw exception text (e.g. database host names, connection errors) | Log errors server-side and only respond with `"error"` |
| Medium | Pages served by Next.js lack the hardening headers Django sends, and advertise `X-Powered-By: Next.js` | Add `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`; disable `X-Powered-By` |
| Medium | No Content-Security-Policy on the frontend | Add a nonce-based CSP via Next.js middleware once inline scripts are inventoried |
| Low | `docker-compose.yml` publishes Postgres (5432) and Redis (6379) on all host interfaces | Bind to `127.0.0.1:` or drop the port mappings; local dev only, never use this file in production |
| Low | `.env.example` ships a placeholder `DJANGO_SECRET_KEY` that would be accepted if copied unchanged | Add a production startup check that rejects the placeholder value |
| Low | `django-cors-headers` is a dependency but not installed in `INSTALLED_APPS`, and `CHANNEL_LAYERS` references `channels_redis`, which is not installed | Remove unused configuration; the frontend proxies API calls same-origin, so CORS is not needed |

### A03 — Software Supply Chain Failures

**Controls (CI, every pull request)**

| Job | Tool | Blocks the PR when |
| :--- | :--- | :--- |
| Dependency vulnerability review | `actions/dependency-review-action` | The PR **adds or upgrades to** any package (runtime or dev) with a moderate+ advisory |
| Dependency audit | `uv audit` | Any backend package has a known vulnerability |
| Dependency audit | `npm audit --omit=dev --audit-level=moderate` | Any frontend **runtime** package has a moderate+ advisory |
| Dependency audit | `npm audit --audit-level=moderate` (root) | Commit tooling (commitlint, Husky) has a moderate+ advisory |
| Dependency audit | `npm audit` (frontend, all) | Never — report only, see accepted exceptions |
| Secret scan | TruffleHog | A verified secret is found anywhere in the repository |

Dependabot ([.github/dependabot.yml](../.github/dependabot.yml)) opens weekly update PRs for `uv` and `npm`, and monthly
PRs for root tooling, GitHub Actions and Docker base images. Commit messages use `chore(deps)` to satisfy commitlint.

**Accepted exceptions (dev tooling only)**

| Package | Advisory | Why accepted | Exit plan |
| :--- | :--- | :--- | :--- |
| `braces` / `micromatch` / `fast-glob` / `chokidar` (via `tailwindcss@3`, `eslint-config-next`, Jest) | GHSA-vfj7-8cjw-p6xm (ReDoS / stack exhaustion), plus related moderate advisories | Build and test tooling only; never shipped to browsers or the server bundle, and only processes the team's own source files. The only fix is the breaking upgrade to Tailwind 4 | Open a Git Issue to migrate to Tailwind 4 before Prototype 3, then make the full `npm audit` step blocking again |

**Required repository settings (Team Lead)**

These are GitHub settings, not files, and must be configured for the scans to actually block merges:

1. **Settings → Code security**: enable *Dependency graph*, *Dependabot alerts* and *Dependabot security updates*.
2. **Settings → Branches → `main` protection rule → Require status checks to pass**: add
   `Dependency vulnerability review`, `Dependency audit`, `Secret scan`, `Backend lint`, `Frontend lint`,
   `Backend unit tests`, and `Frontend unit tests`.

### A04 — Cryptographic Failures

**Controls**

- `PASSWORD_HASHERS` puts `Argon2PasswordHasher` first; legacy PBKDF2 hashes are upgraded on next login.
- Secrets (`DJANGO_SECRET_KEY`, database/Redis passwords, `BGG_API_TOKEN`, SMTP credentials) are read only from the
  environment; `.env` files are git-ignored and TruffleHog scans every PR.
- HTTPS is enforced with `SECURE_SSL_REDIRECT` and HSTS in production.

**Open items**

- Low: the BGG API token is sent as a bearer header on every request to `boardgamegeek.com` over HTTPS; confirm the
  token is scoped read-only.

### A05 — Injection

**Controls**

- All database access goes through the Django ORM with parameterized queries; catalog search uses
  `primary_name__icontains`.
- BGG XML is parsed with `defusedxml`, which blocks XXE, entity expansion ("billion laughs") and DTD retrieval.
- React escapes rendered strings; there is no `dangerouslySetInnerHTML` in the frontend.

**Open items**

| Severity | Item | Recommendation |
| :---: | :--- | :--- |
| High | `tracking.utils._sync_plays_page` interpolates `bgg_username` directly into the BGG URL, so a username such as `me&username=victim` could inject extra query parameters | Pass the username and page through `requests`' `params`, which URL-encodes them. |

### A06 — Insecure Design

**Controls**

- Throttling: anonymous 60/min, authenticated 300/min, BGG sync 3/min (`BggSyncRateThrottle`).
- `Profile.bgg_username` has a case-insensitive unique constraint, so two QuestLog accounts cannot claim the same BGG
  account and import each other's plays.
- `SessionPlayer` constraints guarantee each participant is exactly one of a registered user or a named guest.

**Open items**

| Severity | Item | Recommendation |
| :---: | :--- | :--- |
| Medium | `GET /api/v1/games/<id>/` fetches any unknown ID from BGG. If the request fails or BGG returns no item, a placeholder `"Unknown"` record is saved permanently, so any authenticated user can fill the catalog with junk rows | Don't persist placeholder rows from the catalog endpoint; return 404/503 instead, and refresh placeholders on a later successful fetch |
| Low | `lookup_value_regex = r"\d+"` accepts IDs larger than Postgres `integer`; saving the placeholder record for such an ID raises a database error (500) | Cap the regex length (e.g. `\d{1,9}`) or validate the range before querying |

### A07 — Authentication Failures

**Controls**

- django-allauth headless with browser sessions (no tokens stored in `localStorage`).
- `ACCOUNT_EMAIL_VERIFICATION = "mandatory"`; email confirmation links expire after 3 days.
- allauth defaults: account-enumeration prevention and rate limits on failed logins, signups and password resets
  (backed by the Redis cache).
- MFA: TOTP, recovery codes and WebAuthn passkeys (`MFA_SUPPORTED_TYPES`).
- Django password validators: similarity, minimum length, common passwords, numeric-only.
- Session lifetime 14 days; `SameSite=Lax` session cookie.

**Open items**

- The frontend MFA setup page is still a stub on `main` (now behind `FEATURE_MFA_SETUP`); the working flow is on
  `feature/frontend-mfa-integration`.

### A08 — Software or Data Integrity Failures

**Controls**

- `uv sync --locked` and `npm ci` install exactly what the lockfiles specify.
- `SessionAuthentication` enforces CSRF tokens on unsafe methods; `CSRF_TRUSTED_ORIGINS` is an explicit allow-list.
- Database migrations are linted (`lintmigrations`) and checked for drift in CI.
- Root `npm ci` in CI runs with `--ignore-scripts`.

**Open items**

| Severity | Item | Recommendation |
| :---: | :--- | :--- |
| Medium | CI installs TruffleHog by piping `install.sh` from the `main` branch into `sh` | Pin the script and binary to a release tag, or use the official `trufflesecurity/trufflehog` action at a pinned version |
| Low | Third-party Actions are pinned to major tags (`@v4`), not commit SHAs | Pin to full SHAs; Dependabot's `github-actions` updates keep them current |

### A09 — Security Logging and Alerting Failures

**Current state**: BGG sync and catalog fetch failures are logged at `WARNING`/`ERROR`, and readiness failures are now
logged with stack traces. There is no `LOGGING` configuration, no record of authentication events (failed logins,
MFA changes, password resets), and no alerting.

**Recommendation (Prototype 3)**: add structured JSON logging (timestamp, level, request ID, user ID) as Prototype 3
already requires, connect allauth's signals (`user_logged_in`, `user_login_failed`, MFA authenticator added/removed) to
a security logger, and send errors to Sentry in production.

### A10 — Mishandling of Exceptional Conditions

**Controls**

- BGG network, HTTP and XML errors are caught; the user sees a generic message and details go to the logs.
- `_sync_plays_page` wraps each page in `transaction.atomic()`; a failure part-way rolls back every play on that page
  (covered by `test_sync_rolls_back_every_play_when_one_write_fails`).
- `/ready/` returns 503 when any dependency check fails; the Docker smoke test in CI verifies it.
- Plays with missing IDs or invalid dates are skipped and logged instead of crashing the import.

---

## Data Privacy Controls

| Requirement | Status |
| :--- | :--- |
| Secure password hashing | ✅ Argon2 (`PASSWORD_HASHERS`) |
| Soft delete instead of hard delete | ⚠️ `User.deleted_at` exists (indexed) but no code sets or filters on it yet; play sessions gain `deleted_at` on `feat/basic-analytics`. Related models still use `on_delete=CASCADE` |
| Basic PII protection | ⚠️ PII stored: email, display name, bio, BGG username. Secrets and passwords are never logged. BGG usernames do appear in warning logs |

**Recommendations**: add an account-deletion endpoint that sets `deleted_at`, sets `is_active=False` and replaces the
email with a non-identifying placeholder; give soft-deletable models a default manager that excludes deleted rows.

---

## Feature Flags

Incomplete features are hidden with environment flags so they can ship to `main` without being exposed in staging or
production. Every flag is **off unless explicitly enabled**.

| Flag | Where | Guards |
| :--- | :--- | :--- |
| `FEATURE_ANALYTICS` | backend `.env` | Analytics API (apply `feature_flag = "ANALYTICS"` when `feat/basic-analytics` merges) |
| `FEATURE_BGG_SYNC` | backend `.env` | BGG play-sync endpoint |
| `FEATURE_RECOMMENDATIONS` | backend `.env` | Recommendations API |
| `FEATURE_ANALYTICS` | `frontend/.env` | `/analytics` page (404 when off) |
| `FEATURE_MFA_SETUP` | `frontend/.env` | `/mfa-setup` page (redirects to `/login` when off) |

Backend usage:

```python
from core.feature_flags import FeatureFlagPermission

class AnalyticsSummaryView(APIView):
    feature_flag = "ANALYTICS"
    permission_classes = [FeatureFlagPermission, IsAuthenticated]  # flag first, so anonymous users also get 404
```

Frontend usage: add a `layout.tsx` to the route that calls `await requireFeature("<name>")`
([lib/requireFeature.ts](../frontend/lib/requireFeature.ts)). Frontend flags are read per request, so toggling one
only needs a container restart.

---

## Issues to File

Each open item above should be logged as a Git Issue (label `security`) and closed by the fixing PR:

| Severity | Suggested issue title |
| :---: | :--- |
| Medium | `security: stop persisting placeholder games from the catalog retrieve endpoint` |
| Medium | `security: pin TruffleHog install in CI to a release version` |
| Medium | `security: add Content-Security-Policy to the frontend` |
| Medium | `chore(deps): migrate to Tailwind CSS 4 to clear braces/micromatch advisories` |
| Medium | `feat: account soft delete and PII scrubbing` |
| Low | `security: bound BGG ID lookup to the database integer range` |
| Low | `security: bind Postgres/Redis compose ports to localhost` |
| Low | `security: reject placeholder DJANGO_SECRET_KEY in production` |
| Low | `chore: remove unused CORS and channels configuration` |
| Low | `ci: pin GitHub Actions to commit SHAs` |
| — | `feat: security event logging and alerting` (Prototype 3) |

## Re-audit Triggers

Re-run this checklist when any of the following merges: new write endpoints (play sessions, library, ratings),
permission/role changes (KAN-119), new third-party integrations, or authentication flow changes (frontend MFA).

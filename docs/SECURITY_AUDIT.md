# QuestLog Security Audit — Prototype 2 (OWASP Top 10)

| | |
| :--- | :--- |
| **Audit date** | October 8, 2026 |
| **Baseline** | `feature/prototype-2-security-check` at `d398ab7` (includes the merged library, roles/permissions, recommendations and frontend MFA work) |
| **Scope** | Django backend (`backend/`), Next.js frontend (`frontend/`), Docker Compose stack, GitHub Actions pipeline |
| **Standard** | [OWASP Top 10:2025](https://owasp.org/Top10/) |
| **Method** | Manual code and configuration review, plus automated tooling: TruffleHog (secrets), `uv audit` / `npm audit` / GitHub Dependency Review (dependencies), Ruff + complexipy + ESLint SonarJS (static analysis) |

---

## Summary

| # | Category | Status | Key controls in place |
| :-- | :--- | :---: | :--- |
| A01 | Broken Access Control | ✅ Mitigated | `IsAuthenticated` by default; per-user data scoped with `OwnedQuerysetMixin` + `IsOwnerOrModerator`; role groups (`user`, `moderator`, `admin`); anonymous catalog access is read-only and cannot create records |
| A02 | Security Misconfiguration | ⚠️ Partial | `DEBUG=False` default, HSTS, secure/HttpOnly cookies, frontend hardening headers, readiness probe no longer leaks errors; feature flags declared but **not enforced**; no CSP |
| A03 | Software Supply Chain Failures | ✅ Mitigated | Dependency Review blocks new CVEs on PRs; `uv audit` + runtime `npm audit` gate; Dependabot; 0 runtime vulnerabilities (dev-tooling exception documented) |
| A04 | Cryptographic Failures | ✅ Mitigated | Argon2 password hashing; secrets only via env; HTTPS redirect + HSTS (1 year, preload) in production |
| A05 | Injection | ✅ Mitigated | Django ORM only; `defusedxml` for all BGG XML; React escapes output; BGG username URL-encoded; all query parameters validated by serializers |
| A06 | Insecure Design | ⚠️ Partial | Rate limiting per scope; library adds require a cached game; recommendation consent model; placeholder-game and seed-command risks remain |
| A07 | Authentication Failures | ⚠️ Partial | allauth: mandatory email verification, enumeration protection, rate limits, MFA (TOTP, recovery codes, passkeys) with re-authentication before enrolment; frontend login cannot complete an MFA challenge yet |
| A08 | Software or Data Integrity Failures | ⚠️ Partial | Locked dependency files; CSRF enforced; migrations linted; TruffleHog install script and Actions not pinned |
| A09 | Security Logging and Alerting Failures | ❌ Gap | Only BGG and readiness failures are logged; no auth/role-change audit trail or alerting (planned for Prototype 3) |
| A10 | Mishandling of Exceptional Conditions | ✅ Mitigated | BGG failures return generic messages; atomic play sync; library conflicts return 409; health probes fail closed (503) |

### Changes since the previous revision of this audit

| Previous finding | Status now |
| :--- | :--- |
| `/ready/` returned raw exception text | ✅ Fixed — errors are logged server-side and the response only says `"error"` ([core/views.py](../backend/core/views.py)) |
| Next.js pages lacked hardening headers and sent `X-Powered-By` | ✅ Fixed — headers added and `poweredByHeader: false` ([next.config.ts](../frontend/next.config.ts)) |
| BGG username interpolated into the plays URL | ✅ Fixed — passed through `requests` `params`, with a regression test ([tracking/utils.py](../backend/tracking/utils.py)) |
| Object-level permissions missing for user-owned data | ✅ Fixed — `IsOwnerOrModerator` + `OwnedQuerysetMixin` merged (KAN-119) |
| Frontend MFA setup page was a stub | ✅ Fixed — TOTP enrolment with password re-authentication merged |
| Library items hard-deleted | ✅ Fixed — `LibraryItem.soft_delete()`; default manager hides deleted rows |
| Placeholder games from catalog lookups | ⚠️ Reduced — anonymous users can no longer trigger BGG fetches; authenticated users still can |

---

## Findings by Category

### A01 — Broken Access Control

#### Controls

- `REST_FRAMEWORK.DEFAULT_PERMISSION_CLASSES = IsAuthenticated` ([settings.py](../backend/config/settings.py)), so new
  endpoints are private unless they opt out. Only `/health/` and `/ready/` use `AllowAny`.
- **Catalog** (`BoardGameViewSet`): `IsAuthenticatedOrReadOnly` with list/retrieve only. Anonymous users can browse
  games that are already cached; `retrieve` uses `get_object()` for them, so they receive 404 for unknown IDs and can
  never trigger a BGG fetch or create a record. Serializers raise on create/update.
- **Library** (`LibraryItemViewSet`): `IsAuthenticated` + `IsOwnerOrModerator`, and `OwnedQuerysetMixin` filters every
  query to `user=request.user`. `moderators_see_all = False`, so even moderators only see their own library; another
  user's entry returns 404. The `user` field is set by the view (`serializer.save(user=request.user)`), never from
  request data, and the game cannot be changed after creation.
- **Recommendations**: every view requires authentication; the profile view always resolves to the requester's own
  profile; `RecommendationFeedbackViewSet` uses the same owner filter with `moderators_see_all = False`.
- **Roles**: a `post_save` signal adds every new user to the `user` group; `moderator` and `admin` groups are created
  by migration and can only be granted through Django admin. `IsModeratorOrAdmin` and `IsAdminRole` are ready for
  admin-only endpoints.
- `OwnedQuerysetMixin` returns an empty queryset for anonymous users, so a view that forgets an authentication check
  still cannot leak private rows.
- Django admin is only routed when `ADMIN_ENABLED=True` (defaults to the value of `DEBUG`).

#### Open items

| Severity | Item | Recommendation |
| :---: | :--- | :--- |
| Low | `IsOwnerOrModerator.has_object_permission` lets moderators act on any object they can reach. Today every view that uses it also sets `moderators_see_all = False`, so this is not reachable, but a future view that keeps the default (`True`) would give moderators write access to other users' data | Decide per view whether moderators may write; consider a read-only moderator permission for future moderation endpoints |

### A02 — Security Misconfiguration

#### Controls

- `DEBUG` defaults to `False`; `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` come from the environment.
- `SECURE_HSTS_SECONDS = 31536000` with subdomains + preload; `SECURE_SSL_REDIRECT` toggled per environment;
  `SECURE_PROXY_SSL_HEADER` set when not in debug.
- Cookies: `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` in production, `HttpOnly` session cookie, `SameSite=Lax`.
- Django sends `X-Frame-Options: DENY` and `X-Content-Type-Options: nosniff`; Next.js pages send `X-Frame-Options`,
  `X-Content-Type-Options`, `Referrer-Policy` and `Permissions-Policy`, and no longer send `X-Powered-By`.
- `/ready/` is public but only reports `"ok"` / `"error"` per dependency; details go to the server log.
- The production backend image runs as the unprivileged `appuser`; the frontend image runs as `nextjs`.
- An empty `DJANGO_SECRET_KEY` makes Django raise `ImproperlyConfigured` instead of running with a blank key.

#### Open items

| Severity | Item | Recommendation |
| :---: | :--- | :--- |
| Medium | **Feature flags are declared but enforced nowhere.** `FEATURE_ANALYTICS`, `FEATURE_BGG_SYNC` and `FEATURE_RECOMMENDATIONS` exist in settings, but no view sets `feature_flag` / uses `FeatureFlagPermission`, so the recommendations API is live regardless of `FEATURE_RECOMMENDATIONS`. On the frontend, `requireFeature()` exists but no route calls it, so `/analytics` (placeholder data) and `/mfa-setup` ignore `FEATURE_ANALYTICS` / `FEATURE_MFA_SETUP` | Add `feature_flag` + `FeatureFlagPermission` to the recommendation views, and add `layout.tsx` gates to `/analytics` and `/mfa-setup` (see [Feature Flags](#feature-flags)) — or remove the flags that are no longer needed so the configuration is not misleading |
| Medium | No Content-Security-Policy on the frontend | Add a nonce-based CSP via Next.js middleware once inline scripts are inventoried |
| Low | `docker-compose.yml` publishes Postgres (5432) and Redis (6379) on all host interfaces | Bind to `127.0.0.1:` or drop the port mappings; local dev only, never use this file in production |
| Low | `.env.example` ships a placeholder `DJANGO_SECRET_KEY` that would be accepted if copied unchanged | Add a production startup check that rejects the placeholder value |
| Low | `django-cors-headers` is a dependency but not in `INSTALLED_APPS`, and `CHANNEL_LAYERS` references `channels_redis`, which is not installed | Remove unused configuration; the frontend proxies API calls same-origin, so CORS is not needed |

### A03 — Software Supply Chain Failures

#### Controls (CI, every pull request)

| Job | Tool | Blocks the PR when |
| :--- | :--- | :--- |
| Dependency vulnerability review | `actions/dependency-review-action` | The PR **adds or upgrades to** any package (runtime or dev) with a moderate+ advisory |
| Dependency audit | `uv audit` | Any backend package has a known vulnerability |
| Dependency audit | `npm audit --omit=dev --audit-level=moderate` | Any frontend **runtime** package has a moderate+ advisory |
| Dependency audit | `npm audit --audit-level=moderate` (root, `npm ci --ignore-scripts`) | Commit tooling (commitlint, Husky) has a moderate+ advisory |
| Dependency audit | `npm audit` (frontend, all) | Never — report only, see accepted exceptions |
| Secret scan | TruffleHog | A verified secret is found anywhere in the repository |

Dependabot ([.github/dependabot.yml](../.github/dependabot.yml)) opens weekly update PRs for `uv` and `npm`, and monthly
PRs for root tooling, GitHub Actions and Docker base images. Commit messages use `chore(deps)` to satisfy commitlint.

**Current results** (re-run against this baseline, including the new `pandas`, `scikit-learn` and `qrcode.react`
dependencies):

| Scope | Result |
| :--- | :--- |
| Backend (`uv audit`, 65 packages) | 0 vulnerabilities |
| Frontend runtime (`npm audit --omit=dev`) | 0 vulnerabilities (`next` pinned at patched `16.3.8`) |
| Root tooling | 0 vulnerabilities |
| Frontend dev tooling (report only) | 28 (21 moderate, 7 high) — all in the accepted exception below |

#### Accepted exceptions (dev tooling only)

| Package | Advisory | Why accepted | Exit plan |
| :--- | :--- | :--- | :--- |
| `braces` / `micromatch` / `fast-glob` / `chokidar` (via `tailwindcss@3`, `eslint-config-next`, Jest) | GHSA-vfj7-8cjw-p6xm (ReDoS / stack exhaustion), plus related moderate advisories | Build and test tooling only; never shipped to browsers or the server bundle, and only processes the team's own source files. The only fix is the breaking upgrade to Tailwind 4 | Open a Git Issue to migrate to Tailwind 4 before Prototype 3, then make the full `npm audit` step blocking again |

#### Required repository settings (Team Lead)

These are GitHub settings, not files, and must be configured for the scans to actually block merges:

1. **Settings → Code security**: enable *Dependency graph*, *Dependabot alerts* and *Dependabot security updates*.
2. **Settings → Branches → `main` protection rule → Require status checks to pass**: add
   `Dependency vulnerability review`, `Dependency audit`, `Secret scan`, `Backend lint`, `Frontend lint`,
   `Backend unit tests`, and `Frontend unit tests`.

### A04 — Cryptographic Failures

#### Controls

- `PASSWORD_HASHERS` puts `Argon2PasswordHasher` first; legacy PBKDF2 hashes are upgraded on next login.
- Secrets (`DJANGO_SECRET_KEY`, database/Redis passwords, `BGG_API_TOKEN`, SMTP credentials) are read only from the
  environment; `.env` files are git-ignored and TruffleHog scans every PR.
- HTTPS is enforced with `SECURE_SSL_REDIRECT` and HSTS in production.
- TOTP secrets and recovery codes are generated and stored by `allauth.mfa`; the frontend only renders the
  provisioning QR code locally (`qrcode.react`) and never sends the secret to a third party.

#### Open items

- Low: the BGG API token is sent as a bearer header on every request to `boardgamegeek.com` over HTTPS; confirm the
  token is scoped read-only.

### A05 — Injection

#### Controls

- All database access goes through the Django ORM with parameterized queries; the only raw SQL is the constant
  `SELECT 1` in the readiness probe. Search filters use `icontains` lookups.
- BGG XML is parsed with `defusedxml`, which blocks XXE, entity expansion ("billion laughs") and DTD retrieval.
- Outbound BGG requests pass user-controlled values (`bgg_username`, page) through `requests` `params`, so they are
  URL-encoded (regression test `test_sync_passes_username_as_encoded_query_parameter`).
- Every API input is validated before use: library `ownership` / `is_played` filters are checked against allow-lists;
  `RecommendationQuerySerializer` restricts `strategy`, `period`, `complexity` and `mood` to choice lists and bounds
  numeric parameters (`limit` 1–50, `players` 1–100, `days` 1–3650, etc.); IDs in URLs are restricted to digits.
- React escapes rendered strings; there is no `dangerouslySetInnerHTML` in the frontend.

### A06 — Insecure Design

#### Controls

- Throttling: anonymous 60/min, authenticated 300/min, recommendations 60/min (endpoint can train the content model
  on a cache miss), BGG sync 3/min.
- Adding a library item or feedback requires the game to already be in the local catalog, so those endpoints never
  trigger outbound BGG requests or create placeholder games.
- Recommendations use a consent model: strategies that read a user's own library, plays or ratings only run when
  `use_personal_data` is true (default false); otherwise the service falls back to catalog-wide strategies. Users who
  are inactive or soft-deleted are excluded from training data.
- Recommendation results are cached per user under a versioned key, and the version is bumped whenever the user's
  library, ratings, plays, feedback or profile change, so stale personal data is not served.
- `Profile.bgg_username` has a case-insensitive unique constraint, so two QuestLog accounts cannot claim the same BGG
  account and import each other's plays.
- Database constraints back the business rules: one active library item per user and game, one rating and one
  feedback per user and game, valid ownership/sentiment values, and a session player is exactly one of a user or a
  guest.

#### Open items

| Severity | Item | Recommendation |
| :---: | :--- | :--- |
| Medium | Any authenticated user can call `GET /api/v1/games/<id>/` for arbitrary IDs. If the BGG request fails or returns no item, a placeholder `"Unknown"` game is saved permanently and never refreshed, so the catalog can be filled with junk rows (anonymous users can no longer do this) | Don't persist placeholder rows from the catalog endpoint; return 404/503 instead, and refresh placeholders on a later successful fetch |
| Medium | `python manage.py seed` deletes **every** user and game before seeding and creates accounts (including `demo@questlog.local`) with the password `password123`. Nothing stops it from running against a staging or production database | Refuse to run unless `DEBUG=True` (or an explicit `--force` flag), and generate random passwords for non-demo users |
| Low | `lookup_value_regex = r"\d+"` accepts IDs larger than Postgres `integer`; saving the placeholder record for such an ID raises a database error (500) | Cap the regex length (e.g. `\d{1,9}`) or validate the range before querying |
| Low | `LibraryItem.house_rules` is an unbounded `TextField` | Add a `max_length` on the serializer field (e.g. 5,000 characters) |

### A07 — Authentication Failures

#### Controls

- django-allauth headless with browser sessions: an HttpOnly session cookie plus a CSRF token; no auth tokens are kept
  in `localStorage` (it only stores the chosen avatar).
- `ACCOUNT_EMAIL_VERIFICATION = "mandatory"`; email confirmation links expire after 3 days.
- allauth defaults: account-enumeration prevention and rate limits on login, failed logins, signups, password resets
  and email confirmation (backed by the Redis cache).
- MFA: TOTP, recovery codes and WebAuthn passkeys (`MFA_SUPPORTED_TYPES`). The frontend MFA setup page requires the
  user to re-enter their password (`/auth/reauthenticate`) before activating TOTP.
- Django password validators: similarity, minimum length, common passwords, numeric-only.
- Session lifetime 14 days; `SameSite=Lax` session cookie.

#### Open items

| Severity | Item | Recommendation |
| :---: | :--- | :--- |
| Medium | The login page cannot complete an MFA challenge: when allauth returns the `mfa_authenticate` flow, the page shows "Your account requires another verification step" but never calls `/_allauth/browser/v1/auth/2fa/authenticate`. Users who enable MFA are locked out of the web app (the backend still enforces MFA correctly) | Submit the code from the existing MFA input to `/auth/2fa/authenticate`, and offer the recovery-code fallback |

### A08 — Software or Data Integrity Failures

#### Controls

- `uv sync --locked` and `npm ci` install exactly what the lockfiles specify; root `npm ci` in CI runs with
  `--ignore-scripts`.
- `SessionAuthentication` enforces CSRF tokens on unsafe methods; `CSRF_TRUSTED_ORIGINS` is an explicit allow-list.
- Database migrations are linted (`lintmigrations`) and checked for drift in CI.

#### Open items

| Severity | Item | Recommendation |
| :---: | :--- | :--- |
| Medium | CI installs TruffleHog by piping `install.sh` from the `main` branch into `sh` | Pin the script and binary to a release tag, or use the official `trufflesecurity/trufflehog` action at a pinned version |
| Low | Third-party Actions are pinned to major tags (`@v4`), not commit SHAs | Pin to full SHAs; Dependabot's `github-actions` updates keep them current |

### A09 — Security Logging and Alerting Failures

**Current state**: BGG sync and catalog fetch failures are logged at `WARNING`/`ERROR`, and readiness failures are
logged with stack traces. There is no `LOGGING` configuration, no record of authentication events (failed logins,
MFA changes, password resets), and no alerting. `RoleAssignmentLog` exists for auditing role changes, but nothing
writes to it yet — granting `moderator` or `admin` in Django admin leaves no audit record.

**Recommendation (Prototype 3)**: add structured JSON logging (timestamp, level, request ID, user ID) as Prototype 3
already requires; connect allauth's signals (`user_logged_in`, `user_login_failed`, MFA authenticator added/removed) to
a security logger; write a `RoleAssignmentLog` row whenever a user's groups change (`m2m_changed` on `User.groups`);
and send errors to Sentry in production.

### A10 — Mishandling of Exceptional Conditions

#### Controls

- BGG network, HTTP and XML errors are caught; the user sees a generic message and details go to the logs.
- `_sync_plays_page` wraps each page in `transaction.atomic()`; a failure part-way rolls back every play on that page
  (covered by `test_sync_rolls_back_every_play_when_one_write_fails`).
- `LibraryItem.add_for_user` locks the soft-deleted row (`select_for_update`) inside a transaction and turns
  duplicate-add races into a `409 Conflict` instead of a database error.
- Recommendation strategies with no data fall back to basic strategies and report a `fallback_reason` instead of
  failing.
- `/ready/` returns 503 when any dependency check fails; the Docker smoke test in CI verifies it.
- Plays with missing IDs or invalid dates are skipped and logged instead of crashing the import.

---

## Data Privacy Controls

| Requirement | Status |
| :--- | :--- |
| Secure password hashing | ✅ Argon2 (`PASSWORD_HASHERS`) |
| Soft delete instead of hard delete | ⚠️ Library items: ✅ `deleted_at` + `soft_delete()`, default manager hides deleted rows, re-adding restores the row. Users: `User.deleted_at` exists (indexed) and the recommender excludes soft-deleted users, but no endpoint sets it, and all user-owned models use `on_delete=CASCADE`, so deleting a user in admin hard-deletes their data |
| Consent for personal data | ✅ Recommendations only use a user's own data after they opt in (`use_personal_data`, default false) |
| Basic PII protection | ⚠️ PII stored: email, display name, bio, BGG username. Passwords and secrets are never logged. BGG usernames appear in warning logs. Opening the recommendation settings creates a `RecommendationProfile` row (`get_or_create`), although `RecommendationProfile.for_user` documents that reads never create one |

**Recommendations**: add an account-deletion endpoint that sets `deleted_at`, sets `is_active=False` and replaces the
email with a non-identifying placeholder; give `User` a default manager that excludes deleted accounts; and make the
profile `GET` return an unsaved default (`RecommendationProfile.for_user`) so a row is only created on `PATCH`.

---

## Feature Flags

Feature flags hide incomplete features in staging and production. Every flag is **off unless explicitly enabled**.

| Flag | Where | Intended to guard | Enforced? |
| :--- | :--- | :--- | :---: |
| `FEATURE_ANALYTICS` | backend `.env` | Analytics API (not merged yet) | — |
| `FEATURE_BGG_SYNC` | backend `.env` | BGG play-sync endpoint (not merged yet) | — |
| `FEATURE_RECOMMENDATIONS` | backend `.env` | `/api/v1/recommendations/*` | ❌ |
| `FEATURE_ANALYTICS` | `frontend/.env` | `/analytics` page (placeholder data) | ❌ |
| `FEATURE_MFA_SETUP` | `frontend/.env` | `/mfa-setup` page | ❌ (MFA setup is now complete — consider removing this flag) |

Backend usage:

```python
from core.feature_flags import FeatureFlagPermission

class RecommendationListView(APIView):
    feature_flag = "RECOMMENDATIONS"
    permission_classes = [FeatureFlagPermission, IsAuthenticated]  # flag first, so anonymous users also get 404
```

Frontend usage: add a `layout.tsx` to the route that calls `await requireFeature("<name>")`
([lib/requireFeature.ts](../frontend/lib/requireFeature.ts)); the example is in
[lib/featureFlags.ts](../frontend/lib/featureFlags.ts). Frontend flags are read per request, so toggling one only
needs a container restart.

---

## Issues to File

Each open item above should be logged as a Git Issue (label `security`) and closed by the fixing PR:

| Severity | Suggested issue title |
| :---: | :--- |
| Medium | `fix: complete the MFA challenge on the login page` |
| Medium | `security: enforce feature flags on recommendations and incomplete frontend routes` |
| Medium | `security: stop persisting placeholder games from the catalog retrieve endpoint` |
| Medium | `security: block the seed command outside development` |
| Medium | `security: pin TruffleHog install in CI to a release version` |
| Medium | `security: add Content-Security-Policy to the frontend` |
| Medium | `chore(deps): migrate to Tailwind CSS 4 to clear braces/micromatch advisories` |
| Medium | `feat: account soft delete and PII scrubbing` |
| Low | `security: bound BGG ID lookup to the database integer range` |
| Low | `security: limit library house_rules length` |
| Low | `fix: don't create a recommendation profile on GET` |
| Low | `security: review moderator write access in IsOwnerOrModerator` |
| Low | `security: bind Postgres/Redis compose ports to localhost` |
| Low | `security: reject placeholder DJANGO_SECRET_KEY in production` |
| Low | `chore: remove unused CORS and channels configuration` |
| Low | `ci: pin GitHub Actions to commit SHAs` |
| — | `feat: security event logging, role-change audit log and alerting` (Prototype 3) |

## Re-audit Triggers

Re-run this checklist when any of the following merges: new write endpoints (play sessions, ratings, analytics, BGG
sync), new role-restricted or moderator endpoints, new third-party integrations, or authentication flow changes (MFA
login challenge, account deletion).

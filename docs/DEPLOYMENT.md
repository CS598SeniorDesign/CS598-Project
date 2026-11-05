# Deploying QuestLog

This guide takes QuestLog from the repository to a live HTTPS site with automatic deployments, backups, error tracking
and uptime monitoring, using **only free services**. The repository already contains everything that runs on the
server; this guide covers the accounts and settings that live outside the repository.

- [How it fits together](#how-it-fits-together)
- [What's in the repository](#whats-in-the-repository)
- [Services and cost](#services-and-cost)
- Checklists:
  1. [Domain name](#1-domain-name)
  2. [DNS (Cloudflare)](#2-dns-cloudflare)
  3. [Server (Oracle Cloud Always Free)](#3-server-oracle-cloud-always-free)
  4. [Prepare the server](#4-prepare-the-server)
  5. [Email (Brevo)](#5-email-brevo)
  6. [BoardGameGeek API token](#6-boardgamegeek-api-token)
  7. [Error tracking (Sentry)](#7-error-tracking-sentry)
  8. [Backup storage (Oracle Object Storage)](#8-backup-storage-oracle-object-storage)
  9. [GitHub: environments, secrets and approvals](#9-github-environments-secrets-and-approvals)
  10. [Configure the server's .env](#10-configure-the-servers-env)
  11. [First deployment](#11-first-deployment)
  12. [Uptime monitoring (UptimeRobot)](#12-uptime-monitoring-uptimerobot)
  13. [Scheduled backups and a restore drill](#13-scheduled-backups-and-a-restore-drill)
  14. [Staging (optional)](#14-staging-optional)
  15. [Release v1.0.0-RELEASE](#15-release-v100-release)
- [Day-to-day operations](#day-to-day-operations)
- [Running a release on one machine](#running-a-release-on-one-machine)

## How it fits together

```
Browser ──HTTPS──▶ Caddy (ports 80/443, free Let's Encrypt certificate)
                     ├── /api/*, /_allauth/*, /health/, /static/*  ──▶ Django (gunicorn)
                     └── everything else                             ──▶ Next.js
                   Django ──▶ PostgreSQL + pgvector, Redis
                   Celery worker + beat ──▶ BGG imports, recommender training, cleanup jobs
                   Nightly cron ──▶ pg_dump ──▶ Oracle Object Storage
                   Errors ──▶ Sentry          Uptime ◀── UptimeRobot polls /health/
```

Every service runs in Docker Compose on one free ARM virtual machine. Only Caddy is reachable from the internet. The
site is served from a single origin, so session cookies and CSRF work exactly as in development.

**Deployments:**

1. A push to `production` (or `main`, for staging) runs CI.
2. When CI passes, the **Deploy** workflow builds the images and pushes them to GitHub Container Registry, tagged
   `sha-<commit>`.
3. It then waits for a reviewer to approve (production only), copies `deploy/` to the server, and runs
   `scripts/deploy.sh`.
4. The script starts the new release and checks that it's healthy. If it isn't, it rolls back to the previous release
   automatically.

## What's in the repository

| File | Purpose |
| :--- | :--- |
| `deploy/docker-compose.prod.yml` | The production stack: Caddy, PostgreSQL + pgvector, Redis, Django, Celery worker and beat, Next.js, and Flower (optional) |
| `deploy/Caddyfile` | HTTPS, routing, blocking of private endpoints (`/ready/`, `/metrics/`, `/admin/`), HSTS |
| `deploy/.env.production.example` | Every setting the server needs, with instructions; copied to `.env` on the server |
| `deploy/scripts/deploy.sh` | Starts a release, waits for health checks, and rolls back automatically (`--rollback` to do it by hand) |
| `deploy/scripts/backup-db.sh` / `restore-db.sh` | Nightly database backup to object storage, and restore |
| `.github/workflows/deploy.yml` | Builds, pushes and deploys after CI passes; can be run by hand to redeploy or roll back |
| `.github/workflows/release-image.yml` | On a `v*` tag: builds amd64 and arm64 images and publishes a GitHub Release |
| `.github/workflows/ci.yml` → `production-images` | Builds the production images on every push and pull request, so a broken image is caught before deploy |
| `backend/config/settings.py` | Sentry (when `SENTRY_DSN` is set) |

## Services and cost

| Need | Service | Cost | Notes |
| :--- | :--- | :--- | :--- |
| Server | Oracle Cloud **Always Free** (Ampere A1, ARM) | $0 | Sign-up asks for a card to verify identity; Always Free resources are not charged |
| Domain | Namecheap or Name.com through the **GitHub Student Developer Pack** | $0 for the first year | The course requires a custom domain. Renewal after a year is paid |
| DNS | Cloudflare Free | $0 | |
| HTTPS certificates | Let's Encrypt, through Caddy | $0 | Renewed automatically |
| Container registry, CI/CD | GitHub Container Registry, GitHub Actions | $0 | Private repos get a monthly Actions minutes allowance; ARM image builds use roughly 20–40 minutes each |
| Email | Brevo Free | $0 | 300 emails/day |
| Backups | Oracle Object Storage (Always Free) | $0 | 20 GB |
| Error tracking | Sentry Developer (free) | $0 | One user, limited events per month |
| Uptime monitoring | UptimeRobot Free | $0 | 5-minute checks |

Free-tier limits change. Check each provider's current terms when you sign up.

---

## 1. Domain name

- [x] Apply for the [GitHub Student Developer Pack](https://education.github.com/pack) with your school email, if you don't
  already have it.
- [ ] From the pack's offers, claim a free domain (Namecheap's `.me` offer or Name.com's offer, whichever is listed).
  Pick a short name, e.g. `questlog.me`.
- [ ] Turn on WHOIS privacy and auto-renew notifications at the registrar.
- [ ] Note the renewal date and cost in the team's notes. The domain is only free for the first year.

## 2. DNS (Cloudflare)

- [x] Create a free account at <https://dash.cloudflare.com/sign-up> and **Add a site** with your domain, choosing the
  Free plan.
- [ ] Copy the two nameservers Cloudflare shows. At your registrar, replace the domain's nameservers with them. This
  can take up to 24 hours to take effect.
- [ ] After creating the server (section 3), add DNS records in Cloudflare:
  - `A` record, name `@`, value = the server's public IP, **Proxy status: DNS only (grey cloud)**.
  - Optional: `A` record `staging` pointing to the staging server.
  - Keep DNS-only so Caddy can get its certificate directly. If you later want Cloudflare's proxy, switch to "Proxied"
    and set **SSL/TLS → Full (strict)**.
- [ ] Check it resolves: `dig +short <your-domain>` should print the server IP.

## 3. Server (Oracle Cloud Always Free)

- [ ] Sign up at <https://signup.cloud.oracle.com>. Choose a home region close to your users; Always Free capacity is
  only in your home region, and you can't change it later.
- [ ] **Compute → Instances → Create instance:**
  - Image: **Canonical Ubuntu 24.04** (the aarch64 build).
  - Shape: **Ampere → VM.Standard.A1.Flex**, **2 OCPUs and 12 GB memory**. The Always Free allowance is 4 OCPUs and
    24 GB in total, so this leaves room for a staging server.
  - Networking: create a new VCN with a public subnet, and **assign a public IPv4 address**.
  - SSH keys: upload your personal public key (`~/.ssh/id_ed25519.pub`; create one with `ssh-keygen -t ed25519`).
  - Boot volume: 100 GB (the Always Free allowance is 200 GB in total).
- [ ] If creation fails with "Out of capacity", retry later or pick another availability domain. A1 capacity is often
  briefly unavailable.
- [ ] **Open ports 80 and 443:** go to Networking → Virtual cloud networks → your VCN → Security Lists → Default →
  **Add Ingress Rules**:
  - Source `0.0.0.0/0`, TCP, destination port `80`.
  - Source `0.0.0.0/0`, TCP, destination port `443`.
  - Optionally UDP `443`, for HTTP/3.
- [ ] Note the instance's public IP and add it to Cloudflare (section 2).
- [ ] Optional but recommended: Oracle may reclaim Always Free instances that stay idle for a long time. Upgrading the
  account to **Pay As You Go** keeps Always Free resources free while exempting them from idle reclamation. Check
  Oracle's current Always Free FAQ before relying on this.

## 4. Prepare the server

Run these over SSH as the default `ubuntu` user: `ssh ubuntu@<server-ip>`.

- [ ] Update the system and enable automatic security updates:
  ```bash
  sudo apt update && sudo apt full-upgrade -y
  sudo apt install -y unattended-upgrades && sudo dpkg-reconfigure -plow unattended-upgrades
  ```
- [ ] **Oracle's Ubuntu images block ports 80/443 in iptables**, even after the security list allows them. Open them
  and save the rules:
  ```bash
  sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
  sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
  sudo iptables -I INPUT 6 -m state --state NEW -p udp --dport 443 -j ACCEPT
  sudo netfilter-persistent save
  ```
- [ ] Install Docker Engine and the Compose plugin, following Docker's
  [Ubuntu instructions](https://docs.docker.com/engine/install/ubuntu/), then check it with `docker compose version`.
- [ ] Create a `deploy` user for GitHub Actions, allowed to run Docker, and the deploy directory:
  ```bash
  sudo adduser --disabled-password --gecos "" deploy
  sudo usermod -aG docker deploy
  sudo mkdir -p /opt/questlog && sudo chown deploy:deploy /opt/questlog
  ```
- [ ] Create an SSH key **only for deployments**. Do this on your own machine, not the server:
  ```bash
  ssh-keygen -t ed25519 -N "" -C "questlog-deploy" -f questlog_deploy_key
  ```
  Then install the public half for the `deploy` user on the server:
  ```bash
  sudo mkdir -p /home/deploy/.ssh
  echo "<contents of questlog_deploy_key.pub>" | sudo tee /home/deploy/.ssh/authorized_keys
  sudo chown -R deploy:deploy /home/deploy/.ssh && sudo chmod 700 /home/deploy/.ssh && sudo chmod 600 /home/deploy/.ssh/authorized_keys
  ```
- [ ] From your machine, record the server's host key for GitHub:
  `ssh-keyscan -t ed25519 <server-ip> > known_hosts_entry`. The private key and this entry go into GitHub in section 9.
  Then delete both local files.
- [ ] Turn off SSH password logins if they're on: in `/etc/ssh/sshd_config`, set `PasswordAuthentication no`, then run
  `sudo systemctl restart ssh`.

## 5. Email (Brevo)

Sign-up requires email verification, so the site can't onboard users without working email.

- [ ] Create a free account at <https://www.brevo.com>.
- [ ] **Senders, Domains & Dedicated IPs → Domains → Add a domain**, enter your domain, and add the DNS records Brevo
  shows (the Brevo code, DKIM and DMARC TXT records) in Cloudflare. Wait for Brevo to show the domain as authenticated.
- [ ] Add a sender, e.g. `noreply@<your-domain>`.
- [ ] **SMTP & API → SMTP:** generate an SMTP key. Note the SMTP server (`smtp-relay.brevo.com`), port `587` and your
  SMTP login. These go into `.env` (section 10).

## 6. BoardGameGeek API token

- [ ] BGG's XML API requires a registered application. Sign in to BoardGameGeek, register an application for QuestLog
  following BGG's XML API documentation, and copy the token it issues. It goes into `.env` as `BGG_API_TOKEN`.

## 7. Error tracking (Sentry)

- [ ] Create a free Developer account at <https://sentry.io/signup/>.
- [ ] **Create a project**, platform **Django**, named `questlog-backend`. Copy the **DSN** (Settings → Projects →
  questlog-backend → Client Keys). It goes into `.env` as `SENTRY_DSN`.
- [ ] **Settings → Developer Settings → Organization Tokens → Create**: copy the token. In section 9 it becomes the
  `SENTRY_AUTH_TOKEN` secret, so each deploy is recorded as a release.
- [ ] Note your organization slug and the project slug (`questlog-backend`). They become the `SENTRY_ORG` and
  `SENTRY_PROJECT` variables.
- [ ] **Alerts → Create alert:** "A new issue is created" in the `production` environment → email the team (or send
  to a Discord/Slack webhook).
- [ ] After the first deploy, check **Crons**: the Celery beat jobs (`train-recommender-nightly` and others) appear
  automatically. Add an alert for missed check-ins.
- Optional later: error tracking for the frontend with `@sentry/nextjs`, once it supports the Next.js version in use.

## 8. Backup storage (Oracle Object Storage)

- [ ] In Oracle Cloud: **Storage → Buckets → Create bucket** named `questlog-backups`, in the default Standard tier,
  with **no public visibility**.
- [ ] Find your **Object Storage namespace** (Tenancy details, or the bucket's details page) and your region identifier
  (e.g. `us-ashburn-1`).
- [ ] **Identity → Users → your user → Customer Secret Keys → Generate secret key.** Copy the secret immediately (it's
  shown once) and the access key.
- [ ] These go into `.env`:
  `BACKUP_S3_ENDPOINT=https://<namespace>.compat.objectstorage.<region>.oraclecloud.com`, `BACKUP_S3_REGION`,
  `BACKUP_S3_BUCKET`, `BACKUP_S3_ACCESS_KEY_ID` and `BACKUP_S3_SECRET_ACCESS_KEY`.
- [ ] Optional: add a lifecycle rule on the bucket to delete objects older than 60 days, as a second safety net.

## 9. GitHub: environments, secrets and approvals

In the repository's **Settings**:

- [ ] **Actions → General → Workflow permissions:** "Read repository contents and packages permissions". The
  workflows ask for anything more themselves.
- [ ] **Environments → New environment `production`:**
  - [ ] **Required reviewers:** add at least one teammate. Every production deploy then waits for approval.
  - [ ] **Deployment branches:** "Selected branches" → `production`.
  - [ ] **Secrets:**

    | Secret | Value |
    | :--- | :--- |
    | `DEPLOY_HOST` | The server's public IP |
    | `DEPLOY_USER` | `deploy` |
    | `DEPLOY_SSH_KEY` | Contents of `questlog_deploy_key` (the private key, including the BEGIN/END lines) |
    | `DEPLOY_KNOWN_HOSTS` | Contents of `known_hosts_entry` |
    | `SENTRY_AUTH_TOKEN` | Sentry organization token (optional) |
  - [ ] **Variables:**

    | Variable | Value |
    | :--- | :--- |
    | `APP_DOMAIN` | e.g. `questlog.me` |
    | `DEPLOY_PATH` | `/opt/questlog` |
    | `SENTRY_ORG` / `SENTRY_PROJECT` | Sentry organization slug / `questlog-backend` |
- [ ] **Repository variables** (Secrets and variables → Actions → Variables):
  - [ ] `IMAGE_PLATFORMS`: optional; defaults to `linux/arm64`, which is what the Oracle server needs.
  - [ ] `BUILD_RUNNER`: optional; set to `ubuntu-24.04-arm` **only if the repository is public**, which builds ARM
    images natively in a few minutes. Otherwise they're built under QEMU emulation, which is slower but works.
- [ ] **Branches → add a rule for `production`:** require a pull request and the CI status checks before merging.
- [ ] After the first deploy, open **Packages** (the organization's or your profile's) → `questlog-backend` and
  `questlog-frontend` → **Package settings**. Confirm the repository has access ("Inherit access from source
  repository"). To let others download the release artifact, change the visibility to Public.

## 10. Configure the server's .env

- [ ] Run **Actions → Deploy → Run workflow** once (environment `production`, image tag empty) and approve it. Its
  "Copy deployment files" step puts `docker-compose.prod.yml`, `Caddyfile`, `scripts/` and `.env.production.example`
  into `/opt/questlog`. The deploy step then stops because `.env` doesn't exist yet, which is expected.
- [ ] On the server, as the `deploy` user (`sudo -iu deploy`):
  ```bash
  cd /opt/questlog
  cp .env.production.example .env
  chmod 600 .env
  nano .env
  ```
  Replace every `<...>` value: the domain, a lowercase GitHub owner in the image names, generated secrets
  (`openssl rand -base64 48 | tr -d '\n/+='`), and the database and Redis passwords (letters and digits only for
  Redis), plus the Brevo, BGG, Sentry and backup values from the sections above.
- [ ] Check nothing is left to fill in: `grep -n '=<' .env` should print nothing.

## 11. First deployment

- [ ] Run **Actions → Deploy → Run workflow** again (environment `production`) and approve it. Watch the "Deploy on
  the server" step; it ends with `Deployed sha-...`. From then on, merging to `production` deploys automatically
  after approval.
- [ ] Open `https://<your-domain>`. The certificate should be valid (issued by Let's Encrypt).
- [ ] On the server, finish setting up the application:
  ```bash
  cd /opt/questlog
  C="docker compose -f docker-compose.prod.yml --env-file .env --env-file .image.env"
  # The site name and domain used in verification and password-reset emails:
  $C exec backend python manage.py shell -c "from django.contrib.sites.models import Site; Site.objects.update_or_create(id=1, defaults={'domain': '<your-domain>', 'name': 'QuestLog'})"
  $C exec backend python manage.py createsuperuser
  # Build the recommender once (Celery beat runs it nightly afterwards):
  $C exec backend python manage.py train_recommender
  ```
- [ ] Sign up with a real email address and confirm the verification email arrives and its link works.
- [ ] Send a Sentry test event and confirm it appears in Sentry:
  `$C exec backend python manage.py shell -c "import sentry_sdk; sentry_sdk.capture_message('QuestLog Sentry test')"`
- [ ] Check `https://<your-domain>/ready/` returns **404**, because it's private on purpose. Readiness is checked on the
  server instead by `deploy.sh`.

## 12. Uptime monitoring (UptimeRobot)

- [ ] Create a free account at <https://uptimerobot.com>.
- [ ] **Add New Monitor:** type HTTP(s), URL `https://<your-domain>/health/`, interval 5 minutes.
- [ ] Alert contacts: add the team's email addresses (and optionally a Discord/Slack webhook).
- [ ] Optional: create a free public status page and link it from the README.
- [ ] Test it: stop the backend for a few minutes (`$C stop backend`, then `$C start backend`) and confirm the alert
  arrives.

## 13. Scheduled backups and a restore drill

- [ ] Run a backup by hand as the `deploy` user, and check it appears in the bucket:
  ```bash
  cd /opt/questlog && sh scripts/backup-db.sh
  ```
- [ ] Schedule it nightly with `crontab -e` as `deploy`:
  ```
  15 3 * * * /opt/questlog/scripts/backup-db.sh >> /opt/questlog/backups/backup.log 2>&1
  ```
- [ ] **Restore drill (do this once before the demo):** restore the latest dump into a scratch database, so production
  data is never touched:
  ```bash
  C="docker compose -f docker-compose.prod.yml --env-file .env --env-file .image.env"
  $C exec -T db sh -c 'createdb -U $POSTGRES_USER restore_check'
  $C exec -T db sh -c 'pg_restore -U $POSTGRES_USER -d restore_check --no-owner' < "$(ls -1t backups/*.dump | head -1)"
  $C exec -T db sh -c 'psql -U $POSTGRES_USER -d restore_check -c "select count(*) from users_user"'
  $C exec -T db sh -c 'dropdb -U $POSTGRES_USER restore_check'
  ```
- [ ] For a real restore, which **replaces all data**, run `sh scripts/restore-db.sh backups/<file>.dump`.

## 14. Staging (optional)

Merges to `main` deploy to the `staging` environment once it's configured. Until then that step is skipped with a
notice.

- [ ] Create a second Always Free instance with the remaining allowance (2 OCPUs, 12 GB), and repeat sections 3–4 for
  it.
- [ ] Add a Cloudflare `A` record `staging` pointing to it.
- [ ] Create a GitHub environment named `staging` with the same secrets and variables, using the staging values (no
  required reviewers). Repeat sections 10–11 with `APP_DOMAIN=staging.<your-domain>` and
  `SENTRY_ENVIRONMENT=staging`. Use a separate backup bucket, or skip backups for staging.

## 15. Release v1.0.0-RELEASE

- [ ] When `main` is final, tag it: `git tag v1.0.0-RELEASE && git push origin v1.0.0-RELEASE`.
- [ ] The **Release images** workflow builds amd64 and arm64 images tagged `v1.0.0-RELEASE`, and creates a GitHub
  Release with `questlog-v1.0.0-RELEASE-deploy.tar.gz` attached. This is the course's containerized artifact.
- [ ] To deploy exactly that release: **Actions → Deploy → Run workflow**, environment `production`, image tag
  `v1.0.0-RELEASE`.
- [ ] Add the live URL, the release link and the uptime status page to the README.

---

## Day-to-day operations

| Task | How |
| :--- | :--- |
| Deploy | Merge to `production` and approve the run in Actions |
| Roll back | **Actions → Deploy → Run workflow**, image tag = an earlier `sha-...` (shown in previous runs' summaries). On the server: `sh scripts/deploy.sh --rollback` |
| Logs | `$C logs -f backend celery-worker` (JSON lines; search by `request_id`) |
| Celery UI | `$C --profile tools up -d flower`, then from your machine `ssh -L 5555:localhost:5555 deploy@<server>` and open <http://localhost:5555>. Set `FLOWER_BASIC_AUTH` in `.env` first |
| Django admin | Off by default (`ADMIN_ENABLED=False`) and blocked by Caddy. Use `manage.py shell` or `createsuperuser` over SSH |
| Change a setting | Edit `/opt/questlog/.env`, then `$C up -d` |
| Disk space | `docker system df`. `deploy.sh` removes unused images built more than two weeks ago |
| Rotate a secret | Change it in `.env` (and in GitHub for deploy secrets), then `$C up -d`. Changing `DJANGO_SECRET_KEY` signs everyone out |

**Migrations** run when the new backend starts, while the old release may still be serving requests. Keep them backward
compatible: add new columns or tables in one release, and remove old ones in a later release.
`manage.py lintmigrations` in CI flags the risky ones.

## Running a release on one machine

Any machine with Docker can run a release:

1. Unpack the release's `questlog-<version>-deploy.tar.gz`.
2. Copy `.env.production.example` to `.env`, and set `APP_DOMAIN=localhost`, the image names and the secrets. The
   SMTP, Sentry and backup values can stay empty.
3. Run `sh scripts/deploy.sh <version>`.

Caddy issues a locally trusted certificate for `localhost`, so the browser may ask you to accept it the first time.
The images are public only if the packages were made public (section 9).

# TravelCRM — Nahd Travels

A multi-tenant SaaS CRM for Umrah, Hajj and Ziyarat travel agencies. Each agency gets its own isolated
workspace for vouchers, packages, inventory, ledger, team and attendance, in **English, Urdu and Arabic**
(right-to-left supported).

![Django](https://img.shields.io/badge/Django-6.0-0C4B33) ![Python](https://img.shields.io/badge/Python-3.12-3776AB)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-336791) ![HTMX](https://img.shields.io/badge/HTMX-UI-3D72D7)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED)

---

## Contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [How tenant isolation works](#how-tenant-isolation-works)
- [Getting started (local)](#getting-started-local)
- [Configuration](#configuration)
- [Running the tests](#running-the-tests)
- [Production deployment](#production-deployment)
- [Backups](#backups)
- [Project structure](#project-structure)
- [Translations](#translations)
- [Contributing](#contributing)

---

## Features

**Vouchers and approvals**
- One voucher worksheet (travellers, hotels, flights, transport, team contacts, special instructions) shared by
  the office team and agents.
- Agents submit vouchers for approval; the team approves or sends them back with a reason.
- Printable voucher and PDF (headless Chromium, so the PDF matches the screen), plus a public share link.

**Catalogue**
- Hotels, flights and transport inventory.
- Umrah/Hajj packages with room-sharing prices, departure and return baggage, and customisable "what's included" items.

**Finance**
- Ledger with party balances (Debit − Credit), foreign-currency entries, Excel download and printable statements.
- Collecting a payment on a voucher writes the ledger entry automatically.

**People**
- Team management with fully customisable roles and per-area permissions (view / manage).
- Contacts directory and the voucher instructions printed on every voucher.
- Staff attendance: office hours, Wi-Fi / rotating QR / GPS check-in rules, correction requests.

**Insights**
- Dashboard plus voucher, approval and inventory insights pages with charts and Excel exports.
- Activity Log of every create, edit and delete.

**Platform**
- Subscription plans and billing, with an admin-editable plan catalogue.
- Email notifications (voucher generated, payment receipt) with a delivery log.
- Optional AI assistant (Google Gemini) that answers questions about the agency's data; anything it would
  change is only proposed and needs confirmation.
- Platform admin area for the SaaS operator: agencies, plans, payments, announcements, system health.

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, Django 6.0, Django REST Framework (JWT), drf-spectacular |
| Frontend | Server-rendered Django templates with HTMX, Chart.js, flatpickr |
| Database | PostgreSQL 18 with Row-Level Security |
| Background jobs | Celery + Redis |
| PDF | Headless Chromium (falls back to xhtml2pdf) |
| AI | Google Gemini (optional) |
| Production | Docker Compose, gunicorn, Caddy (automatic HTTPS), WhiteNoise |

## How tenant isolation works

Every agency's data is separated in **two independent layers**:

1. **Application layer** — tenant-owned models use a `TenantManager` that scopes every query to the
   signed-in user's agency (set per request by `utils.middleware.TenantMiddleware`).
2. **Database layer** — PostgreSQL Row-Level Security policies on tenant tables. In production the app connects
   as the restricted `travelcrm_app` role (not the table owner), so even a query that forgot its agency filter
   cannot read another agency's rows. Migrations run separately as the owner.

`tests/test_tenant_isolation.py` proves both layers.

## Getting started (local)

**Requirements:** Python 3.12, PostgreSQL 18, and Docker (for Redis). Google Chrome is optional; PDFs use it
when it is installed.

```bash
git clone https://github.com/WALEED-WAHEED/TravelCRM.git
cd TravelCRM

python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt -r requirements-dev.txt
```

Create the database and the restricted app role (as the PostgreSQL admin):

```bash
createdb -U postgres travelcrm
psql -U postgres -d travelcrm -v app_password='choose-a-password' -f scripts/init-scoped-role.sql
```

Create `.env` (see [Configuration](#configuration)), then:

```bash
docker compose up -d redis        # Redis for background jobs
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver        # http://127.0.0.1:8000
```

**Docker instead of runserver:** `docker compose up -d` starts Redis, the web app and the Celery worker on port
8000, using the PostgreSQL installed on your machine (`host.docker.internal`). The compose file also has an
optional bundled database: `docker compose --profile bundled-db up -d`.

Useful URLs: `/member/dashboard/` (agency app), `/platform-admin/` (SaaS operator), `/admin/` (Django admin),
`/api/docs/` (API documentation), `/health/` (health check).

## Configuration

Settings are read from environment variables, in this order of precedence:
**real environment variables → `.env.local` → `.env`**. Both files are gitignored.

| Variable | Purpose |
|---|---|
| `DJANGO_DEBUG`, `DJANGO_SECRET_KEY`, `ALLOWED_HOSTS` | Core Django settings (a real secret key is required when DEBUG is off) |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Database connection |
| `SCOPED_DB_USER`, `SCOPED_DB_PASSWORD` | The `travelcrm_app` role (used by the isolation tests, and by the app in production) |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Redis URLs |
| `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | Outgoing email |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | AI assistant (optional) |
| `FRONTEND_URL` | Public address used in QR codes and links |

A typical local setup keeps shared values in `.env` and machine-specific ones (e.g. `DB_HOST=localhost`) in
`.env.local`.

## Running the tests

```bash
python -m pytest tests/           # needs PostgreSQL and the travelcrm_app role (SCOPED_DB_PASSWORD in .env)
python -m ruff check .
python manage.py check
```

The suite (about 200 tests) covers tenant isolation, permissions, vouchers, ledger, notifications, billing and
the pages themselves. Celery tasks run inline during tests.

## Production deployment

Production runs everything on one server with Docker Compose: PostgreSQL 18, Redis, the web app, the Celery
worker and Caddy, which obtains and renews the HTTPS certificate automatically.

1. Point your domain's DNS **A record** at the server and open ports **80** and **443**.
2. Copy the environment template and fill it in (domain, secret key, two database passwords, email):

   ```bash
   cp env.production.example .env.production
   ```

3. Start it:

   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
   ```

On the first start the database creates the `travelcrm_app` role, a one-off `migrate` service applies the
migrations as the database owner, and the web app and worker start as `travelcrm_app` — so Row-Level Security
is enforced. `DEBUG` is off, HTTP redirects to HTTPS and cookies are secure; all of that is fixed in
`docker-compose.prod.yml`, so only the values in `.env.production` vary per server.

**Updating:** pull the new code and run the same `up -d --build` command; pending migrations are applied
automatically before the app restarts.

**Staging:** run the same file on a separate server with its own `.env` file (e.g. `DOMAIN=staging.example.com`).

## Backups

The production database and uploaded images live in Docker volumes on the server. They survive restarts,
rebuilds and updates, but **not** the loss of the server itself. The `backup` service in
`docker-compose.prod.yml` therefore runs every night (`BACKUP_TIME`, UTC):

- dumps the database and keeps the latest 14 dumps on the server;
- with `R2_*` and `BACKUP_PASSPHRASE` set in `.env.production`, encrypts each dump and the uploaded images on the
  server and copies them to a **Cloudflare R2** bucket (free up to 10 GB), keeping the latest 14 dumps there too;
- shows as `unhealthy` in `docker compose ps` if no backup has succeeded for 26 hours.

Keep `BACKUP_PASSPHRASE` in a password manager as well: without it the R2 copies cannot be restored. Code
comes back from GitHub, and voucher PDFs are generated on demand, so neither needs a backup.

```bash
DC="docker compose -f docker-compose.prod.yml --env-file .env.production"
$DC run --rm --no-deps backup now                      # back up immediately
$DC run --rm --no-deps backup list                     # dumps stored in R2
$DC run --rm --no-deps backup restore latest           # safe test: restores into travelcrm_restore_test
```

**Disaster recovery (new server):** clone the repo, put the same `.env.production` in place, then

```bash
$DC up -d db
$DC run --rm --no-deps backup restore latest --force-target   # database + images; asks for confirmation
$DC up -d --build
```

The restore also re-applies the `travelcrm_app` grants. On an existing server stop the app first
(`$DC stop web worker`). The scripts underneath are described in `scripts/README.md`:

- `scripts/offsite-backup.sh` — the schedule, the R2 copy and the restore commands above.
- `scripts/backup.sh` — timestamped, compressed `pg_dump`, keeping the latest 14.
- `scripts/restore.sh` — restores into a throwaway database by default (safe to test any time).
- `python manage.py verify_backup` — dumps, restores and compares row counts to prove a backup is usable.

## Project structure

```
travelcrm/        Django settings, URLs, Celery app
member/           Core agency app: vouchers, packages, inventory, ledger, contacts, attendance, insights
agent/            Agent portal (reuses the voucher worksheet)
accounts/         Custom user model (role, agency, profile photo, language)
agencies/         Agency (the tenant)
rbac/             Roles, permissions, Team & Roles pages, Activity Log
billing/          Plans, subscriptions, billing page, subscription gate
payments/         Collected payments, payment plans, supplier payments
notifications/    Email notifications, delivery log, notification settings
system_config/    Branding, audit log, platform configuration
platform_admin/   SaaS operator area
assistant/        Gemini AI assistant
utils/            Tenancy, middleware, audit and API helpers
templates/        Shared templates (base layout, member pages, public voucher)
static/           CSS, JavaScript, vendored libraries and fonts
locale/           Urdu and Arabic translations
scripts/          Database role, backup and restore scripts
tests/            pytest suite
```

## Translations

The interface is available in English, Urdu (Noto Nastaliq) and Arabic (Noto Naskh), with full right-to-left
layout. Each user picks their language under **Settings → My profile**. Catalogues live in
`locale/{ur,ar}/LC_MESSAGES/django.po` and are compiled to `.mo`; every new user-visible string needs both an
Urdu and an Arabic translation.

## Contributing

Read [`CLAUDE.md`](CLAUDE.md) before making changes. It is the project's working agreement: the required
workflow, database and tenant-isolation rules, UI components to reuse, and how to verify a change (checks,
tests, and a real browser at desktop and phone width).

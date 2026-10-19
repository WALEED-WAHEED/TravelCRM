# TravelCRM (Nahd Travels) — multi-tenant SaaS CRM for Umrah/Hajj travel agencies

> **Read this whole file before every development task, and follow it.** It is the standing set of rules for
> this project. If a request conflicts with a rule here, say so before acting. Keep this file current: when you
> learn a lasting fact about the project (a convention, a pitfall, a decision), update the relevant section.

Django 6.0 + DRF + HTMX templates, PostgreSQL 18 (required — RLS), Celery/Redis, Gemini AI assistant.
Python 3.12 in `.venv/`. UI in English, Urdu and Arabic (RTL).

---

## 1. Required workflow (every task)

1. **Read this file.**
2. **Inspect before touching anything** — the relevant code, templates, URLs, models *and the live database*
   (schema, constraints, indexes, row counts). For codebase questions run `graphify query "<question>"` first
   (see §11). Never assume the code or schema is well-structured; look.
3. **Find the root cause / real requirement.** Reproduce bugs. Check whether an existing model, view, partial,
   helper or CSS component already does the job before creating anything new.
4. **Plan the smallest clean change** that fits the existing architecture.
5. **Implement** following every rule below.
6. **Review** the change for: extra DB queries (N+1), extra HTTP/API calls, blocking work in the request,
   tenant isolation, authorization, validation, error handling, cost (Gemini tokens, Chrome PDF renders).
7. **Verify**: `python manage.py check`, `ruff check .`, the relevant tests (full suite when shared code changed),
   and — for UI — load the page in a real browser at desktop **and** phone (≈390px) width.
8. **Report** what changed, what was tested (with real results), what could *not* be tested, remaining issues,
   and any performance/cost impact. Never claim something works or is clean without evidence.

## 2. Commands

- Run: `.venv/Scripts/python manage.py runserver` (or `START_DEV.bat`). Redis for the manual run comes from the
  compose container: `docker compose up -d redis`.
- Docker (dev): `docker compose up -d` = redis, web, worker on port 8000, using the **host's** Postgres via
  `host.docker.internal` (`DOCKER_DB_HOST`); the bundled `db` service (Postgres 18) is opt-in (`--profile bundled-db`).
  Run one of manual/Docker at a time (both use 8000). The image includes Chromium, so Docker PDFs match the View page.
- **Production/staging**: `docker-compose.prod.yml` + `Caddyfile` + `env.production.example` (copy to
  `.env.production`). Caddy terminates HTTPS (automatic Let's Encrypt) and serves `/media/`; `DEBUG` off, secure
  cookies and `SECURE_PROXY_SSL_HEADER` are fixed in the file. A one-off `migrate` service runs as the DB owner;
  web/worker run as `travelcrm_app` (real RLS). `scripts/init-scoped-role.sql` (via `init-scoped-role.sh` on a fresh
  volume, `psql -v app_password=… -f` by hand, and in CI) creates that role with default privileges on future tables.
  Postgres 18 images mount their volume at `/var/lib/postgresql` (not `/data`).
- Env files: `.env` (shared, also read by compose) and `.env.local` (this machine's overrides, e.g. `DB_HOST`).
  Precedence: real environment variables > `.env.local` > `.env` (`travelcrm/settings.py`). Both are gitignored.
- Test: `.venv/Scripts/python -m pytest tests/` (~6 min on an idle machine; needs Postgres + scoped role `travelcrm_app` — create it with `psql -v app_password=… -f scripts/init-scoped-role.sql` — and `SCOPED_DB_PASSWORD` in `.env`). Run long suites in the background. `tests/conftest.py` runs Celery tasks inline, so a running Redis/worker never receives test notifications.
- Lint: `.venv/Scripts/python -m ruff check .` · Check: `python manage.py check` · CI: `.github/workflows/ci.yml`
- Migrations: write them with `makemigrations`, but **never run `migrate` on the user's database** — tell the user to run it.
- Dev server reload after Python edits: touch `member/templatetags/currency_tags.py`.
- Translations: edit `locale/{ur,ar}/LC_MESSAGES/django.po` with `polib` and compile `.mo` (no GNU gettext on this machine). Every new user-visible string needs Urdu **and** Arabic.
  Pitfalls: `{% trans "Rate (%)" %}` is looked up with the `%` doubled, so the msgid must be `Rate (%%)`;
  `{% blocktrans count %}` needs a plural entry (`msgid_plural`); model `choices`/`verbose_name` must use
  `gettext_lazy`. English names stored in the DB (standard role names, plan names, delivery-log details) are
  translated at display time with the `tr` filter (`{% load i18n_extra %}`, `member/templatetags/i18n_extra.py`).
  Urdu uses Noto Nastaliq Urdu and Arabic Noto Naskh Arabic (Google Fonts in every page head; rules in `app.css`).

## 3. Database & PostgreSQL rules

- **Inspect first.** Before creating/altering/dropping a table or column, query the live schema
  (`information_schema`, `pg_indexes`, `pg_constraint`, row counts) and read the model + its migrations.
- **No blind or duplicate structures.** Reuse existing tables/columns; no redundant columns, no parallel tables
  for the same concept, no denormalised copies unless they are deliberate snapshots (see booking line items).
- **Every tenant-owned model**: `agency` FK, `objects = TenantManager()`, `all_tenants = UnscopedManager()`,
  `Meta.base_manager_name = 'all_tenants'`, a `*_row_level_security` migration, and a test in
  `tests/test_tenant_isolation.py`. Index FKs and any column used for filtering/sorting at scale.
- **Queries**: no N+1 — use `select_related`/`prefetch_related`/annotations; aggregate in SQL, not Python loops,
  when data can grow; paginate lists; never load whole tables into memory for display.
- **Migrations** must be reversible where practical; data migrations use `apps.get_model` + `_base_manager`.
- Known state (audit 2026-10-19): 66 tables, all 122 FKs indexed, 28 tables with RLS (29 once
  `notifications/0004_deliverylog_row_level_security` is migrated). Deliberate exceptions without RLS:
  `accounts_user` (auth model) and `system_config_auditlog` (see its migration 0010). RLS is **inert for the
  role the app runs as** (`postgres` superuser in dev `.env`; a table owner in the production example), so
  isolation in the running app relies on `TenantManager`; only the `scoped` test connection proves RLS.
  To get real RLS at runtime run the app as the non-owner `travelcrm_app` role (set `DB_USER`/`DB_PASSWORD` to the
  `SCOPED_DB_*` values) and run `migrate` with the owner: `DB_USER=postgres DB_PASSWORD=… manage.py migrate`.
  Verified 2026-10-14: every member page returns 200 as `travelcrm_app`. `tenant_context()` mirrors tenant/bypass
  onto the DB session GUCs (and restores them on exit), so commands/tasks work under that role too.
  Unused legacy tables: `member_hotelroom`, `member_hotelimage`, `member_flightsegment`,
  `member_bookingteamcontact` (0 rows). `member_voucher`/`member_voucherservice` belong to the **old** agent
  voucher flow (see §6) — do not build new features on them.

## 4. Clean, maintainable code

- Follow the existing structure and naming; match surrounding style and comment density.
- Prefer extending an existing module over adding a file. Before creating a file/dir, check whether it belongs
  in an existing one. No dead code, duplicate helpers, commented-out blocks, stray scripts or temp files in the
  repo (scratch work goes in the session scratchpad). Remove what you replace.
- Don't add dependencies without need; check `requirements.txt` first.
- **Git**: the project is pushed to `github.com/WALEED-WAHEED/TravelCRM` (`master`). Don't commit or push unless
  asked; keep `.claude/settings.json` (machine-specific paths) out of commits.

## 5. UI: responsive, consistent, accessible

- Every page, table, form, modal and drawer must work at **≥1280px, ~768px and ~390px**. No page may scroll
  sideways; wide tables scroll inside their own `overflow-x:auto` wrapper. Use relative units, `minmax(0,1fr)`
  grids and `min-width:0` on flex/grid children. Test in a real browser at phone width before reporting done.
- The shell is responsive: below 1023px the sidebar is an off-canvas menu (`initSidebar()` in `app.js`,
  `.sidebar.mobile-open` + backdrop) and `.main-content` has `min-width:0`. Verified 2026-10-14 with no sideways
  page scroll on 17 pages at 390px and 768px — keep it that way.
- Reuse the existing components instead of inventing new ones:
  - Page header: `hotels-hero` (eyebrow + title, **no subtitle line**), actions in `hotels-hero__actions` with a gap.
  - Stat cards: `hotels-stat-grid` / `hotels-stat-card`; tables: `hotels-data-table` inside a scroll wrapper.
  - Row actions: round icon buttons `.vx-actions > .vx.vx--view|--edit|--del|--ok|--pdf` (never text buttons).
  - Pop-ups: `.modal-overlay` + `.modal-box`, opened with `openModal(id)`; detail views use a side drawer
    (`.modal-overlay.drawer-wrap > aside.drawer`). `app.js` moves overlays to `<body>` (animated ancestors
    break `position:fixed`); any custom floating menu must also be attached to `<body>`.
  - Confirmations: never `confirm()` — add `data-confirm="…" data-confirm-title data-confirm-ok [data-confirm-danger]`
    to the `<form>`; `app.js` shows the shared `#app-confirm` dialog (markup in `base.html`).
  - Dropdowns: `SelectMenu.init(root)` (`static/js/select-menu.js`); dates: vendored flatpickr.
  - Settings tabs (`member/partials/settings_nav.html`): My profile (everyone, `member/account_views.py`),
    Company profile (owner; branding, Shirka partner, live voucher-header preview, notification switches),
    Attendance (owner). The old Language and Notifications pages redirect into these.
  - Insights pages: `member/inventory_insights.py` (declarative KPIs/sections) + `templates/member/inventory_insights.html`;
    voucher/approval insights have their own modules. Charts via Chart.js 4.4.0.
    Shared period/KPI helpers live in `member/analytics.py` (xlsx styling: `member/xlsx.py`). There is no standalone
    Reports page — each section has its own insights; the `activity_log` capability guards the Activity Log.
- RTL: use logical properties (`inset-inline-*`, `margin-inline-*`), test `dir="rtl"`.

## 6. Domain map & invariants

- **Apps** (routes in `travelcrm/urls.py`): `member/` (core domain + most UI; `views.py` ≈2030 lines — prefer
  new focused modules like `note_views.py`, `instruction_views.py`, `account_views.py`, `*_insights.py`), `agent/` (agent portal,
  reuses member views/forms), `agencies/` (Agency = tenant), `accounts/` (custom `User`: `role`, `agency`,
  `custom_role`), `rbac/` (`engine.has_capability(user, cap, 'view'|'manage')` = single authz source; Activity Log),
  `system_config/` (branding, AuditLog …), `billing/`, `payments/`, `notifications/`,
  `platform_admin/`, `assistant/` (Gemini chat; write tools only create a PendingAction), `utils/`.
- **Tenant isolation**: context from `utils.middleware.TenantMiddleware` (session) / `utils.api.TenantScopedAPIMixin`
  (JWT DRF — must be mixed in). Outside requests: `with tenant_context(agency_id=…)` / `tenant_context(bypass=True)`.
- **Authz**: new views use `rbac.decorators.permission_required(cap, action)`; legacy `member_required` /
  `agent_required` bridge via `role_level`. Agents only ever see/edit their own records. Every view needs one
  of these decorators (a view without one 500s for signed-out visitors — `profile` did until 2026-10-19).
- **Roles**: each agency owns its roles. On first use `rbac.views._tenant_roles()` copies the four global
  templates into the agency (`Agency.roles_seeded`) and moves its users onto the copies; after that roles are
  added/edited/deleted in the Roles pop-up. You can't delete your own role or the last role, or remove your own
  `team:manage`. Deleting a role leaves its users on the legacy access for their `User.role`.
- **Removing a teammate is a soft delete** (`User.deleted_at` + `is_active=False`): they vanish from Team and can't
  sign in, but bookings/payments/vouchers keep them (those FKs are `CASCADE` — never hard-delete a user who has any).
- **Notifications**: only `voucher_generated` (booking confirmed) and `payment_receipt` (a `BookingPayment` is
  collected — manual ledger entries don't send) are dispatched (`notifications/signals.py`). The header bell
  lazy-loads the latest delivery-log rows from `notifications-recent` when opened.
- **Vouchers = `Booking`.** Status: `draft` (Drafted), `pending` (submitted by an agent), `rejected` (Sent back,
  with `rejection_reason`), `confirmed`/`completed` (Saved/Approved), `cancelled` (hidden). One shared form
  (`booking_voucher_worksheet.html`, `worksheet_save(request, actor)`) serves team and agents. Approvals page =
  pending only; approved → Vouchers list; rejected → back to the agent. Line items snapshot catalog fields.
- **Audit**: `utils/audit.register_audited_models()` logs create/update/delete via signals — register new
  models there; use `log_event()` only for changes signals can't see (e.g. voucher line items). Don't hand-log otherwise.
- **Ledger**: party balance = Debit − Credit (Dr = party owes agency); `LedgerEntry.save()` converts FX and assigns `trans_no`.
- **Attendance**: self check-in rules in `member/attendance.py`; office timezone from `AttendanceSettings.time_zone` (server is UTC).
- **Voucher print/PDF**: one template `voucher_document.html`; PDF is printed by headless Chrome
  (`member/pdf_chrome.py`, falls back to xhtml2pdf) so it matches the View page.

## 7. Asynchronous work & request handling

- Keep the request path fast. Slow or external work (email, notifications, exports of large data, LLM calls,
  PDF rendering) should run in Celery or be bounded with explicit timeouts and user-visible loading/error states.
- Current state (audit 2026-10-14): only one Celery task exists (`notifications.send_notification_task`, falls
  back to inline). **Blocking in-request work**: Gemini calls (`assistant/engine.run_turn`, up to 5 tool rounds;
  bounded by `GEMINI_TIMEOUT_MS`, default 30s, errors become `AssistantProviderError`), Chrome PDF (`subprocess`, 60s timeout), Excel exports. Don't add more without a reason.
- Frontend: debounce search inputs (HTMX `keyup changed delay:350ms`), disable submit buttons after the submit
  starts (use `setTimeout` — disabling inside the click handler cancels the submit in Chrome), avoid duplicate
  requests, never poll the server without need (current `setInterval`s are client-only clocks).

## 8. API, cost & performance

- For every endpoint/call ask: what does it do, when, how often, is it needed, can it be merged/cached/batched?
- Watch paid/limited resources: Gemini tokens (history of up to 20 messages is re-sent each round), Chrome PDF
  CPU, email sending. Never trade correctness, security or tenant isolation for fewer calls.
- Baseline (audit): ~9 queries of per-request overhead (session, user, 2×`set_config`, subscription, role,
  agency, SaaS config, announcements, branding) — candidates for caching. Pages are 13–40 queries.
  The attendance and package-insights N+1s were fixed (2026-10-14).
- No caching backend is configured (`CACHES` defaults to per-process LocMem) and `CONN_MAX_AGE` is 0.
- External assets load from CDNs without SRI (`unpkg` HTMX, `jsdelivr` Chart.js, Google Fonts).

## 9. Testing & verification

- Understand current behaviour before changing it; add/adjust tests in `tests/` for every behaviour change
  (tenant isolation, permissions, numbers, exports).
- After changes: `manage.py check`, `ruff check .`, relevant pytest files, then the full suite for shared code.
- UI: verify in headless Chrome (CDP scripts in the scratchpad; log in as `member` / `012345678` on the dev
  server) at desktop and phone widths; kill only your own headless Chrome processes.
- Report exact results; list anything not tested. `ruff check .` is clean — keep it that way.

## 10. Data you create while testing

Test rows in the user's dev database must be tagged (e.g. `DEMO`, `TMPA-`, `DEMO-AG-`) and removed afterwards
unless the user asked to keep sample data. Never delete user data you didn't create.

## 11. graphify

This project has a knowledge graph at `graphify-out/`.
- For codebase questions, first run `graphify query "<question>"` when `graphify-out/graph.json` exists. Use
  `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts.
- If `graphify-out/wiki/index.md` exists, use it for broad navigation instead of raw source browsing.
- Read `graphify-out/GRAPH_REPORT.md` only for broad architecture review.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

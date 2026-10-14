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

- Run: `.venv/Scripts/python manage.py runserver` (or `START_DEV.bat`; Docker: `docker-compose.yml` = db, redis, web, worker)
- Test: `.venv/Scripts/python -m pytest tests/` (~8 min; needs Postgres + scoped role `travelcrm_app`, see `scripts/init-scoped-role.sql`). Run long suites in the background.
- Lint: `.venv/Scripts/python -m ruff check .` · Check: `python manage.py check` · CI: `.github/workflows/ci.yml`
- Migrations: write them with `makemigrations`, but **never run `migrate` on the user's database** — tell the user to run it.
- Dev server reload after Python edits: touch `member/templatetags/currency_tags.py`.
- Translations: edit `locale/{ur,ar}/LC_MESSAGES/django.po` with `polib` and compile `.mo` (no GNU gettext on this machine). Every new user-visible string needs Urdu **and** Arabic.

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
- Known state (audit 2026-10-14): 66 tables, every FK indexed, 28 tables with RLS. RLS is **inert for the
  role the app runs as** (`postgres` in dev; in Docker the app user owns the tables and `FORCE RLS` is off), so
  isolation in the running app relies on `TenantManager`; only the `scoped` test connection proves RLS.
  Unused legacy tables: `member_hotelroom`, `member_hotelimage`, `member_flightsegment`,
  `member_bookingteamcontact` (0 rows). `member_voucher`/`member_voucherservice` belong to the **old** agent
  voucher flow (see §6) — do not build new features on them.

## 4. Clean, maintainable code

- Follow the existing structure and naming; match surrounding style and comment density.
- Prefer extending an existing module over adding a file. Before creating a file/dir, check whether it belongs
  in an existing one. No dead code, duplicate helpers, commented-out blocks, stray scripts or temp files in the
  repo (scratch work goes in the session scratchpad). Remove what you replace.
- Don't add dependencies without need; check `requirements.txt` first (note: `pandas` is pinned but unused).
- **Git**: much of the project is currently *untracked* (tests/, rbac/, billing/, payments/, many migrations,
  utils/tenancy.py …). Don't assume `git status` reflects reality; don't commit unless asked.

## 5. UI: responsive, consistent, accessible

- Every page, table, form, modal and drawer must work at **≥1280px, ~768px and ~390px**. No page may scroll
  sideways; wide tables scroll inside their own `overflow-x:auto` wrapper. Use relative units, `minmax(0,1fr)`
  grids and `min-width:0` on flex/grid children. Test in a real browser at phone width before reporting done.
- **Known defect (audit 2026-10-14):** the app shell has no mobile breakpoint — `.sidebar` stays fixed open
  and `.main-content` keeps `margin-inline-start: var(--sidebar-width)` with `min-width:auto`, so nearly every
  page scrolls sideways at 390px and most at 768px. Fix this before claiming any page is responsive.
- Reuse the existing components instead of inventing new ones:
  - Page header: `hotels-hero` (eyebrow + title, **no subtitle line**), actions in `hotels-hero__actions` with a gap.
  - Stat cards: `hotels-stat-grid` / `hotels-stat-card`; tables: `hotels-data-table` inside a scroll wrapper.
  - Row actions: round icon buttons `.vx-actions > .vx.vx--view|--edit|--del|--ok|--pdf` (never text buttons).
  - Pop-ups: `.modal-overlay` + `.modal-box`, opened with `openModal(id)`; detail views use a side drawer
    (`.modal-overlay.drawer-wrap > aside.drawer`). `app.js` moves overlays to `<body>` (animated ancestors
    break `position:fixed`); any custom floating menu must also be attached to `<body>`.
  - Dropdowns: `SelectMenu.init(root)` (`static/js/select-menu.js`); dates: vendored flatpickr.
  - Insights pages: `member/inventory_insights.py` (declarative KPIs/sections) + `templates/member/inventory_insights.html`;
    voucher/approval insights have their own modules. Charts via Chart.js 4.4.0.
- RTL: use logical properties (`inset-inline-*`, `margin-inline-*`), test `dir="rtl"`.

## 6. Domain map & invariants

- **Apps** (routes in `travelcrm/urls.py`): `member/` (core domain + most UI; `views.py` ≈2050 lines — prefer
  new focused modules like `note_views.py`, `instruction_views.py`, `*_insights.py`), `agent/` (agent portal,
  reuses member views/forms), `agencies/` (Agency = tenant), `accounts/` (custom `User`: `role`, `agency`,
  `custom_role`), `rbac/` (`engine.has_capability(user, cap, 'view'|'manage')` = single authz source; Activity Log),
  `system_config/` (branding, AuditLog …), `billing/`, `payments/`, `notifications/`, `reports/`,
  `platform_admin/`, `assistant/` (Gemini chat; write tools only create a PendingAction), `utils/`.
- **Tenant isolation**: context from `utils.middleware.TenantMiddleware` (session) / `utils.api.TenantScopedAPIMixin`
  (JWT DRF — must be mixed in). Outside requests: `with tenant_context(agency_id=…)` / `tenant_context(bypass=True)`.
- **Authz**: new views use `rbac.decorators.permission_required(cap, action)`; legacy `member_required` /
  `agent_required` bridge via `role_level`. Agents only ever see/edit their own records.
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
  back to inline). **Blocking in-request work**: Gemini calls (`assistant/engine.run_turn`, up to 5 tool rounds,
  no explicit HTTP timeout), Chrome PDF (`subprocess`, 60s timeout), Excel exports. Don't add more without a reason.
- Frontend: debounce search inputs (HTMX `keyup changed delay:350ms`), disable submit buttons after the submit
  starts (use `setTimeout` — disabling inside the click handler cancels the submit in Chrome), avoid duplicate
  requests, never poll the server without need (current `setInterval`s are client-only clocks).

## 8. API, cost & performance

- For every endpoint/call ask: what does it do, when, how often, is it needed, can it be merged/cached/batched?
- Watch paid/limited resources: Gemini tokens (history of up to 20 messages is re-sent each round), Chrome PDF
  CPU, email sending. Never trade correctness, security or tenant isolation for fewer calls.
- Baseline (audit): ~9 queries of per-request overhead (session, user, 2×`set_config`, subscription, role,
  agency, SaaS config, announcements, branding) — candidates for caching. Pages are 13–40 queries.
  Known N+1: `/member/attendance/` (attendance logs + roles per staff member), Package insights (`agent` per voucher).
- No caching backend is configured (`CACHES` defaults to per-process LocMem) and `CONN_MAX_AGE` is 0.
- External assets load from CDNs without SRI (`unpkg` HTMX, `jsdelivr` Chart.js, Google Fonts).

## 9. Testing & verification

- Understand current behaviour before changing it; add/adjust tests in `tests/` for every behaviour change
  (tenant isolation, permissions, numbers, exports).
- After changes: `manage.py check`, `ruff check .`, relevant pytest files, then the full suite for shared code.
- UI: verify in headless Chrome (CDP scripts in the scratchpad; log in as `member` / `012345678` on the dev
  server) at desktop and phone widths; kill only your own headless Chrome processes.
- Report exact results; list anything not tested. Current lint debt: 12 ruff findings (pre-existing).

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

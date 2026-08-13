# Austin Limo Shuttle — Django backend

Replacement for the legacy PHP 5.4 booking application at austinlimoshuttle.com.
This repository holds the Django backend, the staff dashboard and the REST API
that the Next.js frontend will consume.

**Read first:** `security-issue.html` documents live vulnerabilities in the
production system that are independent of this rebuild and need the client's
attention regardless of when it ships.

## Documents

| File | What it is |
|---|---|
| `security-issue.html` | Findings in the live legacy system, ordered by severity |
| `legacy-app-brief.html` | File-by-file map of the old application and its schema |
| `new-build-brief.html` | Target architecture, data model, delivery plan |
| `docs/qa/phase-*.md` | QA report per build phase, with defects found and decisions taken |

Two corrections to the client documents, recorded in the QA reports: the server
runs **MariaDB 10.11**, not MySQL 8, and **3 of 36** CMS pages carry encoding
damage, not 29.

## Requirements

- Python 3.12 (matches InMotion's `alt-python312`)
- Docker (for the local MariaDB 10.11, matching production exactly)

## Setup

```bash
# 1. Database — MariaDB 10.11, plus the sanitised legacy replica
docker compose -f ops/docker-compose.yml up -d
./ops/load-legacy.sh

# 2. Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt
cp .env.example .env          # defaults work against the compose database
python manage.py migrate
python manage.py sync_roles   # Dispatcher / Manager / Editor groups
python manage.py createsuperuser
```

## Importing the legacy data

Order matters — bookings reference vehicles and customers.

```bash
python manage.py import_fleet      # vehicles + distance bands
python manage.py import_pricing    # surcharges, blackout dates, tax rate
python manage.py import_members    # 1,251 customers (passwords are discarded)
python manage.py import_orders     # 2,217 bookings + payment records
python manage.py import_content    # pages, banners, enquiries (repairs mojibake)
```

Every importer is idempotent and supports `--dry-run` and `--limit N`.

**No importer reads a card column or a password column.** The replica is checked
for cardholder data before any import runs, and the run aborts if it finds any.

## Verifying the pricing engine

The most valuable check in the project: replay nine years of real bookings
through the new fare engine and diff against what was actually charged.

```bash
python manage.py replay_fares --report
```

Expect ~100% agreement for 2026 and ~92% for 2025, falling off for older years.
That is rate-card drift, not a defect — the legacy database stores only the
*current* rate card, so bookings priced under older rates cannot be reproduced.
See `docs/qa/phase-3.md` for the evidence. **An engine bug would fail 2026 too.**

## Running

```bash
python manage.py runserver
```

| URL | What |
|---|---|
| `/dashboard/` | Staff dashboard — dispatch board, bookings, enquiries |
| `/admin/` | Django admin — fleet, rates, content, users |
| `/api/` | REST API for the frontend |

## Tests

```bash
pytest                    # everything (~7 min; legacy-replica tests are slow)
pytest -m "not legacy"    # unit only (~10 s)
ruff check .              # lint
```

The `legacy` mark means a test needs the sanitised replica loaded.

## Deployment

```bash
./ops/deploy-rehearsal.sh   # installs into a clean 3.12 venv and boots prod settings
./ops/check-wheels.sh       # every prod dependency must have a Linux wheel
```

Run `check-wheels.sh` after **any** change to `requirements/base.txt`. The target
host has no C compiler, so a package that only ships an sdist fails at deploy
time — long after it was added. This is why the project uses PyMySQL rather than
`mysqlclient`, and xhtml2pdf rather than WeasyPrint.

The InMotion deployment procedure is in `docs/qa/phase-7.md`.

## Project layout

```
backend/
├── accounts/      custom User (email login), addresses, corporate accounts
├── fleet/         vehicles and their distance-band rate cards
├── pricing/       surcharges, blackout dates, and engine.py — the fare logic
├── bookings/      bookings, price lines, drivers, status audit trail
├── payments/      Stripe references only; no field can hold a card number
├── content/       CMS pages, banners, testimonials, site settings
├── enquiries/     contact / service / corporate enquiries
├── dashboard/     staff views + templates, role definitions
├── api/           DRF endpoints and signed quote tokens
└── legacy_import/ one-shot import commands and the mojibake repair
ops/               docker compose, legacy loader, deployment scripts
docs/qa/           per-phase QA reports
```

## Design decisions worth knowing

**Prices are computed server-side, always.** The API has no field that can carry
a price. Booking requires a signed, short-lived quote token, and the fare is
recomputed before anything is stored. The legacy funnel carried the fare in
`$_SESSION` and re-derived it at payment — same trust, more steps.

**Cardholder data has nowhere to go.** `payments.Payment` stores a Stripe
reference, a brand and a last-4 (a 4-character column). A test scans every model
for a field that could hold a card number and every stored value for a
card-shaped string.

**Legacy passwords were discarded, not migrated.** All 1,251 imported accounts
have an unusable password and must reset before signing in. **This needs
customer communication at launch** or it will look like a breach notification.

**Distance bands and surcharge windows are data, not code.** Legacy hardcoded
the 6/50/100-mile boundaries as PHP constants, and described the late-night
window in prose while the real hours sat in PHP — so the admin screen described
behaviour the system did not have.

**Surcharges are additive.** A 40% event date at 22:00 is +60%, not +68%.
Compounding them would overcharge every surcharged booking by ~5%.

**Every status change records who made it.** The legacy system had one shared
admin login, so no action could be attributed to anyone.

## Known gaps

- **Stripe is not wired up.** Models exist; `POST /api/bookings/` leaves the
  booking `pending`. This is the next piece of work.
- **No password-reset flow yet.** Required at launch for the imported accounts.
- **Two vehicles cannot be priced** — Chrysler 300 Limousine and Lincoln
  Limousine have all-zero rates in the legacy data. On the old site they would
  quote $0.00. Needs a client decision: deactivate, or supply rates.
- **This project is not under version control.** `.gitignore` is prepared and
  excludes `.env`, `.secrets/`, `legacy/` and `dumps/`.

## API documentation

```
/api/docs/     Swagger UI   — try requests against a running server
/api/redoc/    ReDoc        — easier to read end to end
/api/schema/   OpenAPI 3.1  — machine-readable
docs/openapi.yaml            — checked-in snapshot for the frontend
```

Open in development; **staff-only in production**, because the schema lists
every endpoint, its throttles and its error shapes.

Generate a typed TypeScript client for the Next.js app:

```bash
npx openapi-typescript docs/openapi.yaml -o frontend/lib/api-types.ts
```

Re-export the snapshot after changing any endpoint:

```bash
cd backend && python manage.py spectacular --file ../docs/openapi.yaml
```

`--fail-on-warn` is part of the test suite, so an endpoint added without a
schema annotation fails CI rather than shipping undocumented.

### The two rules the schema encodes

**No endpoint accepts a price or a distance.** `POST /api/quotes/` takes two
addresses and returns a signed `quote_token`; `POST /api/bookings/` takes that
token and the server recomputes the fare. Tests assert the request schemas have
no such properties.

**Payment is confirmed by webhook, not by the browser.** A successful card
confirmation client-side does not mark a booking paid — Stripe calls
`/api/payments/webhook/` and that is what confirms it. The frontend should show
a pending state and poll `/api/account/bookings/{reference}/`.

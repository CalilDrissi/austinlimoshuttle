# Phase 0 QA Report — Scaffolding & Environment

**Date:** 12 August 2026
**Status:** ✅ Passed — exit criteria met

---

## Exit criteria

| # | Criterion | Result |
|---|---|---|
| 1 | Clean `migrate` against MariaDB 10.11 | ✅ 13 tables created |
| 2 | Test suite runs | ✅ 32 passed |
| 3 | `runserver` boots, `/admin/` renders | ✅ HTTP 200, CSRF token present |
| 4 | `check --deploy` reviewed | ✅ 0 issues with a real secret key |
| 5 | `AUTH_USER_MODEL` set before first migration | ✅ locked by test |

## Automated results

```
pytest        32 passed in 1.74s
ruff          All checks passed!
check (dev)   System check identified no issues (0 silenced).
check --deploy  System check identified no issues (0 silenced).
check-wheels  OK: all 33 packages available as Linux wheels
```

## Manual QA checklist

| Check | Result |
|---|---|
| Local DB version matches production | ✅ `10.11.18-MariaDB` local vs `10.11.18-MariaDB` on InMotion |
| Database charset is utf8mb4 end to end | ✅ asserted by test |
| 4-byte characters survive a round trip | ✅ `Zoë 🚗` stored and re-read intact |
| Admin login page renders with correct branding | ✅ `<title>Log in \| Austin Limo Shuttle</title>` |
| Admin index, user list, user add, user change render | ✅ all HTTP 200 |
| Superuser can log in | ✅ |
| Anonymous user redirected from admin | ✅ |
| Non-staff user cannot reach admin | ✅ |
| Imported-style account has no usable password | ✅ `has_usable_password() == False` |
| `passenger_wsgi.py` imports under prod settings | ✅ returns `WSGIHandler` |
| Legacy replica loaded and sanitised | ✅ 2,217 orders / 1,251 members / 0 cardholder values |

## Defects found and fixed

**1. Admin "add user" page returned HTTP 500.**
`add_form = UserCreationForm` lacks the `usable_password` field that Django 5.1+
expects in `add_fieldsets`, raising `FieldError` on render. Replaced with
`AdminUserCreationForm`, which also supports deliberately creating an account
with no usable password — the state every imported legacy customer starts in.
Found by manual QA, not by unit tests. `accounts/tests/test_admin.py` now covers
every admin page so this class of failure is caught automatically.

**2. Adding a user silently failed with no error shown.**
`BillingAddressInline` rendered on the add page, so `all_valid(formsets)` failed
whenever the management form was absent — the page re-rendered with an empty
`form.errors`, giving no indication of what went wrong. Inlines are now hidden
on the add view via `get_inlines()`; an address cannot belong to a user that
does not exist yet.

## Decisions recorded

**MariaDB 10.11, not MySQL 8.** The production server reports
`10.11.18-MariaDB`. `new-build-brief.html` §13 says MySQL 8 and is superseded.
A test asserts the local version matches, so drift fails the suite.

**xhtml2pdf over WeasyPrint.** WeasyPrint needs cairo/pango system libraries
that cannot be installed on shared cPanel hosting.

**PyMySQL over mysqlclient.** No C compiler on the target host.

**The no-compiler constraint is verified, not assumed.** `ops/check-wheels.sh`
resolves every production dependency against `manylinux2014_x86_64` / cp312.
All 33 packages — including `cryptography`, `cffi`, `lxml` and `Pillow` — are
available as wheels. Note `cryptography` *did* compile from source during local
macOS install; only the Linux answer matters, and it is clean. Re-run this after
any change to `requirements/base.txt`.

**Password hashing is not weakened outside tests.** The fast MD5 hasher lives in
`config/settings/test.py` only, never in `dev.py`, so it cannot reach an
environment holding real user data.

## Notes carried forward

- **`user_email` is dead.** Populated in 0 of 1,251 legacy rows. `email` is the
  login identity — confirmed at `execute_function.php:470`, which compares with
  `BINARY`, making legacy login case-sensitive. All 1,251 addresses remain
  distinct when lowercased, so normalising on import is safe. **This unblocks
  Phase 1.**
- **This project is not under version control.** `.gitignore` is prepared and
  excludes `.env`, `.secrets/`, `legacy/` and `dumps/`, but no repository has
  been initialised. Worth doing before Phase 1 adds substantial code.
- `SECRET_KEY` warning (`security.W009`) appears only when passing a dev key;
  with a generated key the deployment check is clean.

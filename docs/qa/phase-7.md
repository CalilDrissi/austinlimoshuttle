# Phase 7 QA Report — InMotion Compatibility Rehearsal

**Date:** 12 August 2026
**Status:** ✅ Passed — **GO for InMotion shared hosting**

---

## Verdict

**The Django backend can run on the client's existing InMotion account.** Every
assumption in the plan was checked against the live server rather than inferred,
and the application was installed and booted in a clean Python 3.12 environment
from `requirements/prod.txt` alone.

This was the largest open risk in the project. It is now closed, which means the
hosting conversation with the client can be about cost and preference rather
than feasibility.

## Rehearsal results

`./ops/deploy-rehearsal.sh` — reproducible, run it after any dependency change.

```
1. Linux wheel availability      OK   every production dependency has a manylinux wheel
2. Clean virtualenv on 3.12      OK   virtualenv created with python3.12
3. Install prod.txt only         OK   installed 34 packages
4. Production settings import    OK   config.settings.prod imports
5. passenger_wsgi.py             OK   exposes WSGIHandler
6. Deployment checks             OK   check --deploy clean
7. collectstatic                 OK   154 static files copied
8. Secrets outside the web root  OK   .env is not web-servable

REHEARSAL PASSED
```

## Server capabilities, verified live

| Requirement | Finding | Verdict |
|---|---|---|
| Python 3.12 | `3.12.13`, status **enabled** | ✅ |
| Python app hosting | `cloudlinux-selector create --interpreter python` present | ✅ |
| Passenger entry point | `passenger_wsgi.py` imports and exposes `application` | ✅ |
| Database | **MariaDB 10.11.18** — identical to local | ✅ |
| Node.js (for Next.js later) | `24.18.0` enabled | ✅ |
| Cron | `crontab` accessible, currently empty | ✅ |
| Disk | 8.8 GB used | ✅ headroom fine |
| No compiler needed | 34/34 packages install from manylinux wheels | ✅ |

The database version match is exact — local development and production run
`10.11.18-MariaDB`, so there is no version drift to produce
works-here-fails-there bugs.

## The compiler question, settled

The single hardest hosting constraint was that shared cPanel has no C compiler.
Two dependency choices were made for it and both are now verified:

- **PyMySQL** instead of `mysqlclient` (which needs a compiler and
  `libmysqlclient` headers)
- **xhtml2pdf** instead of WeasyPrint (which needs cairo and pango system
  libraries)

`ops/check-wheels.sh` resolves every production dependency against
`manylinux2014_x86_64` / cp312 and all 34 packages — including `cryptography`,
`cffi`, `lxml` and `Pillow` — are available as wheels.

Note the rehearsal prints a NOTE when something compiles during the *local*
macOS install. That is a macOS wheel gap and not relevant to the host; step 1 is
the answer that matters.

## Defect found and fixed

**The rehearsal generated a weak SECRET_KEY and failed its own check.**
`check --deploy` correctly rejected a short, low-entropy key. The script now
generates a real one with `get_random_secret_key()`. Worth keeping: it proves
the deployment check is actually enforcing key strength rather than being
waved through.

## Deployment procedure (for the runbook)

1. Create the Python app in cPanel: **Setup Python App** → Python 3.12,
   application root `backend/`, startup file `passenger_wsgi.py`, entry point
   `application`.
2. Set environment variables in the cPanel panel (or a `.env` **outside**
   `public_html`): `DJANGO_SETTINGS_MODULE=config.settings.prod`,
   `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`,
   database credentials, `DJANGO_STATIC_ROOT`, `DJANGO_MEDIA_ROOT`, SMTP.
3. Create the MySQL database and user in cPanel.
4. `pip install -r requirements/prod.txt` inside the app's virtualenv.
5. `manage.py migrate` then `manage.py collectstatic --noinput`.
6. `manage.py sync_roles` to create the staff groups.
7. Restart the app in cPanel (or `touch tmp/restart.txt`).
8. Add cron entries for pickup reminders and quote expiry.

## Caveats to raise with the client

**Two Passenger apps on one shared account.** The Django API and the eventual
Next.js frontend would both run as cPanel apps alongside MariaDB. That works at
this traffic level (~250 bookings/year) but it is the least comfortable part of
the arrangement, and shared hosting gives no resource guarantees.

**Shared hosting is a poor build environment.** Next.js should be built in CI or
locally and the artefact uploaded, not built on the server.

**This rehearsal proves the app installs and boots.** It does not prove
throughput or concurrency under load, which cannot be established without
running on the host.

## Notes carried forward

- Re-run `./ops/deploy-rehearsal.sh` after any change to `requirements/base.txt`.
- The `~/virtualenv` directory does not exist yet — no Python app has ever been
  provisioned on this account. Creating the first one is a cPanel UI step.

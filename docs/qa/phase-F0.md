# Phase F0 QA Report — Frontend Scaffold & Asset Lift

**Date:** 13 August 2026
**Status:** ✅ Passed

---

## Exit criteria

| # | Criterion | Result |
|---|---|---|
| 1 | Next.js project builds | ✅ |
| 2 | Template CSS and fonts render | ✅ all assets 200 |
| 3 | Typed API client generated from our schema | ✅ 17 endpoints |
| 4 | A page renders live data from Django | ✅ |

## Results

```
next build      ✓ compiled, 2 routes
tsc --noEmit    clean
backend pytest  375 passed
backend ruff    All checks passed
check-wheels    46/46 Linux wheels
```

Live check against the running Django server:

```
/                                              200
/styles/luxride.css                            200
/fonts/7e6a2e30184bb114-s.p.woff2              200
/fonts/uicons-regular-rounded.866b86e7.woff2   200
/assets/imgs/template/logo.svg                 200

vehicles from the API: Business Class, Business SUV, Mercedes Sprinter
```

## What was lifted from the mirror

| Asset | Count / size | Handling |
|---|---|---|
| Images | 187 files, 9.4 MB | `public/assets/imgs/`, unchanged |
| Compiled CSS | 418 KB | `public/styles/luxride.css`, kept verbatim |
| Fonts | 5 files | `public/fonts/` — DM Sans + Flaticon UIcons |

## Defects found and fixed

**1. The CSS hotlinked 11 assets from the demo site.**
The scraper rewrote relative URLs to absolute ones pointing at
`https://luxride-nextjs.vercel.app/...`. Left alone, our site would have loaded
images from someone else's deployment — working locally, and breaking whenever
that demo changed or went away. All 11 rewritten to local paths.

Six of them were jQuery-UI icon sprites whose paths the scraper had mangled
(`/_next/static/css/%22images%2Fui-icons_...%22`). Those files are not in the
mirror and nothing in our ten pages uses jQuery UI, so they now resolve to
`none` rather than to a 404 on a third-party host.

**2. Fonts referenced a directory that does not exist here.**
`@font-face` used `../media/...`, which resolved to `/_next/static/media/` on
the original deployment. Our stylesheet lives at `/styles/`, so those became
`/media/` — silently missing. Copied the five font files to `/public/fonts/` and
rewrote the directory with one generic rule rather than per-file special cases.

Both would have produced a site that *looked* right in review and degraded
later. Verified: 5 font references, 0 missing.

**3. The API had no CORS headers, and `django-cors-headers` was not installed.**

This is the one worth dwelling on. Server-rendered pages fetch from Node to
Django and never trigger CORS, so the scaffold worked perfectly while the
configuration was entirely absent. The booking funnel calls the API **from the
browser** — quotes, bookings, payment intents, sign-in — and every one of those
would have been blocked, in F3, with a confusing browser-console error rather
than a server-side failure.

Added and configured with explicit origins. `CORS_ALLOW_ALL_ORIGINS` is off and
a test asserts it stays off: credentials are permitted, and a wildcard origin
combined with credentials would let any site issue authenticated requests as a
signed-in customer. Seven tests cover the headers, preflight, the `X-CSRFToken`
allowance, and middleware ordering.

## Decisions recorded

**Next 16.3, not 15.** `create-next-app` installs current; the plan said 15.
No functional difference for this build. Recorded so the plan and reality agree.

**No Tailwind.** It would fight the template CSS — Preflight resets exactly the
element styling the template relies on.

**The template stylesheet is loaded from `/public`, not imported.** It is a
vendored artefact kept byte-identical so it can be swapped or replaced wholesale
later. Our own changes go in `app/globals.css` instead, so the two never tangle.

**The API client has no helper that accepts a price or a distance.** The
backend refuses both; the client makes them inexpressible rather than merely
unused.

## Notes carried forward

- **Origins are configured for localhost.** Production needs
  `DJANGO_CORS_ALLOWED_ORIGINS` and `DJANGO_CSRF_TRUSTED_ORIGINS` set to the
  real domain. Still better: put both apps under one parent domain so the
  session cookie works without cross-origin machinery at all — undecided.
- **`npm run api:types`** regenerates the client types from
  `docs/openapi.yaml`. Run it after any backend endpoint change.
- The images are the template's stock photography, retained for the validation
  build per the client and to be replaced before production.

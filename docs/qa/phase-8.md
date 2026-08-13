# Phase 8 QA Report — Security Hardening & Handover

**Date:** 12 August 2026
**Status:** ✅ Passed — build complete

---

## Exit criteria

| # | Criterion | Result |
|---|---|---|
| 1 | No critical findings | ✅ |
| 2 | A clean checkout reproduces the environment from the README | ✅ rehearsed |
| 3 | Security review over auth and booking paths | ✅ 15 regression tests |

## Final results

```
pytest    271 passed  (234 unit + 37 legacy-replica), 0 warnings
ruff      All checks passed!
check     System check identified no issues
rehearsal REHEARSAL PASSED — 8/8 steps
```

## Legacy findings, and what closes each

Every critical finding in `security-issue.html` is addressed **structurally** —
by making the defect inexpressible — rather than by policy or vigilance.

| Legacy finding | Resolution | Enforced by |
|---|---|---|
| 3,416 plaintext card numbers | No model has a field that could hold one | `test_no_model_has_a_cardholder_field` |
| 68 retained CVVs | Never collected; no field exists | same |
| — | No stored value matches a card pattern | `test_no_stored_value_looks_like_a_card_number` |
| 1,251 plaintext passwords | PBKDF2; legacy passwords discarded entirely | `test_passwords_are_hashed` |
| 27 SQL injection sites | ORM parameterises everything; raw SQL banned in app code | `test_application_code_contains_no_raw_sql_execution` |
| Unauthenticated booking read | Scoped to `customer=request.user`; foreign refs 404 | `test_another_customer_gets_404_not_403` |
| Client-controlled prices | Signed quote token; server recomputes; no price field exists | `test_booking_uses_the_server_price_not_the_clients` |
| Stripe key in the web root | Environment variable; media outside `public_html` | `test_media_root_is_outside_the_web_root` |
| No CSRF | Django CSRF middleware | `test_csrf_middleware_is_enabled` |
| No HSTS / insecure cookies | HSTS 1 year, Secure + HttpOnly, SSL redirect | `test_production_settings_are_hardened` |
| No rate limiting | DRF throttles on auth, quote and enquiry | `test_sensitive_scopes_are_configured` |
| Single shared admin login | Three role groups; every status change attributed | Phase 5 tests |
| PHP 5.4, unpatched 11 years | Python 3.12 / Django 5.2 LTS | — |

Added this phase: **Content-Security-Policy** and **Permissions-Policy** headers
via a 40-line middleware rather than a new dependency. `script-src` deliberately
does *not* grant `unsafe-inline`; `style-src` must, because Django's admin
depends on inline styles.

## The card-data scan

`test_no_stored_value_looks_like_a_card_number` walks every `CharField` and
`TextField` on every application model and matches each stored value against
`^\d{13,19}$`. It runs against the real imported dataset — 2,217 bookings, 1,251
customers, 928 enquiries — and finds nothing. This is the check that would catch
card data arriving through a route nobody anticipated, such as a customer typing
a number into a notes field.

## Defect found and fixed

**pytest tried to collect a database model as a test class.** The `Testimonial`
model matches pytest's `Test*` collection pattern, producing a
`PytestCollectionWarning` on every run. Suppressed with `__test__ = False` on
the model. Trivial, but a warning that is always present is a warning nobody
reads.

## Handover

`README.md` covers setup, the import sequence, the fare replay, tests,
deployment, and the design decisions worth knowing. It was written to be
followed from a clean checkout.

Also documented there, and worth repeating:

**Legacy passwords were discarded, not migrated.** All 1,251 imported accounts
have an unusable password. **This needs customer communication before launch**
— an unannounced "reset your password" email to 1,251 people reads exactly like
a breach notification.

**Two vehicles cannot be priced.** Chrysler 300 Limousine and Lincoln Limousine
carry all-zero rates in the legacy data; the old site would quote **$0.00** for a
real journey. The engine refuses instead. Needs a client decision.

**This project is not under version control.** `.gitignore` is prepared and
correctly excludes `.env`, `.secrets/`, `legacy/` and `dumps/`, but no
repository has been initialised.

## Not in this build

- **Stripe integration.** Models exist; no API calls. `POST /api/bookings/`
  leaves the booking `pending`.
- **Password reset flow.** Required at launch.
- **Next.js frontend.**
- **Transactional email templates.** The backend sends nothing yet; SMTP is
  configured for production but no message templates exist.

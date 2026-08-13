# Phase 11 QA Report — Password Reset

**Date:** 13 August 2026
**Status:** ✅ Passed — complete

---

## Exit criteria

| # | Criterion | Result |
|---|---|---|
| 1 | Migrated accounts can recover a working login | ✅ verified on real data |
| 2 | Uses Django's built-in views, not hand-rolled | ✅ |
| 3 | No account enumeration | ✅ |
| 4 | API endpoint for the frontend to trigger a reset | ✅ |
| 5 | No bulk mailing | ✅ per client decision |

## Automated results

```
pytest    333 unit passed  (12 password reset), 37 legacy-replica
ruff      All checks passed!
```

## The defect this phase found

**Django's stock `PasswordResetForm` would have locked out all 1,251 migrated
customers, permanently and silently.**

`PasswordResetForm.get_users()` filters on `has_usable_password()`. That default
is sound in general — it stops a reset email reaching an account that
authenticates some other way, such as SSO-only users. It is exactly wrong here:
every migrated customer has an unusable password *by design*, because the legacy
passwords were plaintext and were discarded rather than carried across.

Under the stock form, a returning customer clicking "forgot password" would get
a cheerful "check your email" page and **no email, for ever**. Nothing would
error. Nothing would log. The account holding their booking history would simply
be unreachable.

`accounts/forms.py::MigrationPasswordResetForm` overrides `get_users()` to drop
that one filter and nothing else. The token is still single-use, still expiring,
still sent only to the registered address, and inactive accounts are still
excluded.

Two tests pin this in both directions:

```
test_stock_django_form_would_exclude_them   -> stock form returns []
test_our_form_includes_them                 -> ours returns the account
test_inactive_accounts_are_still_excluded   -> the one filter we keep
```

The first is unusual — a test asserting what the *framework* does — but it is
the reason the override exists, and without it someone would eventually
"simplify" back to the default and silently break account recovery.

## Verified against real imported data

```
real migrated account : sharonkwoodul@gmail.com
can sign in now       : False
emails sent           : 1
can sign in after     : True
login works           : True
bookings still linked : 2
```

A genuine imported customer went from locked out to signed in, with their two
historical bookings still attached.

## What was built

| Route | Purpose |
|---|---|
| `/accounts/password-reset/` | Request a link |
| `/accounts/password-reset/sent/` | Neutral confirmation |
| `/accounts/reset/<uidb64>/<token>/` | Set a new password |
| `/accounts/reset/done/` | Complete |
| `/accounts/password-change/` | Change while signed in |
| `POST /api/auth/password-reset/` | Frontend trigger; always 202 |

All six use `django.contrib.auth.views` — only the templates are ours. Emails
send both a plain-text and an HTML part.

## Scope change: no bulk mailing

The client decided against mass-emailing 1,251 customers. The
`send_launch_password_resets` command and its tests were built and then
**removed**, along with the "we rebuilt the site" wording branch in the email
templates.

Migrated customers now set a password through the ordinary "forgot password"
link, whenever they next book. This is why the `get_users()` override matters
more under this decision, not less: with no proactive mailing, that link is the
*only* path those accounts have to a working login.

## Decisions recorded

**No enumeration, anywhere.** A known and an unknown address produce byte-identical
responses from both the web form and the API — same status, same redirect, same
JSON. Tested explicitly.

**Password strength is enforced on reset.** The project's validators (minimum 10
characters, not common, not numeric) apply; a test confirms `12345678` is
refused and the account stays unusable.

**Reset pages are served by Django, not the frontend.** They are rare,
security-sensitive, and Django's implementation already handles token expiry,
one-time use and invalidation-on-change correctly. Routing them through Next.js
would mean reimplementing that.

## Notes carried forward

- Email currently uses the console backend in development. Production SMTP is
  configured in `config/settings/prod.py` against the existing
  `mail.austinlimoshuttle.com` mailbox but has never sent a real message —
  deliverability is unverified until the first live send.
- Booking confirmation and driver-assignment emails are still to build; this
  phase covered account emails only.

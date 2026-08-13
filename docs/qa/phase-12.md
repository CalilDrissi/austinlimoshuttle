# Phase 12 QA Report — Transactional Email & SMTP Settings

**Date:** 13 August 2026
**Status:** ✅ Passed — complete

---

## Exit criteria

| # | Criterion | Result |
|---|---|---|
| 1 | SMTP credentials managed in the dashboard | ✅ Manager-only, password encrypted |
| 2 | Booking confirmation with PDF attachment | ✅ verified on real data |
| 3 | Driver-assigned, cancellation, reminder, ops alert | ✅ |
| 4 | A mail failure never breaks a booking | ✅ tested |
| 5 | Every attempt recorded | ✅ `EmailLog` |

## Automated results

```
pytest    333 unit passed  (32 notifications), 37 legacy-replica
ruff      All checks passed!
```

## Verified end to end on real data

```
booking: 532361 -> shannonandtodd@yahoo.com
sent    : True
subject : Your booking is confirmed — 532361
parts   : text + html
pdf     : booking-532361.pdf  2,741 bytes
```

## SMTP settings

**Dashboard → Email**, Manager-only, alongside the Stripe page.

| Property | How |
|---|---|
| Password at rest | Fernet-encrypted, shared helper with the Stripe key |
| Password in the UI | Never rendered — `••••26` only |
| Access | Dispatcher gets 403; nav link hidden |
| Test send | One click, records success or the exact error |
| Delivery log | Last 15 messages with outcome, failures counted |

The form flags a port/security mismatch — port 465 with STARTTLS, or 587 with
SSL/TLS. Not fatal, because hosts vary, but worth surfacing: the symptom is a
connection that hangs rather than an error message.

**The test-send button is the important part.** Deliverability is invisible
until something is actually sent, and this is a mailbox nobody has proved works.
It records the outcome on the settings row, so the last known state is visible
without digging through logs.

## Messages

| Trigger | To | Contents |
|---|---|---|
| Payment succeeds (webhook) | Customer | Itinerary, fare breakdown, **PDF attached** |
| Payment succeeds | Operations | New-booking alert with pickup time |
| Driver assigned in dispatch | Customer | Driver name and phone |
| Booking cancelled (staff or customer) | Customer | Refund amount, or the fee that applied |
| 24h before pickup | Customer | Reminder with driver if assigned |
| Manual test | Chosen address | Proves the SMTP settings |

All render a plain-text and an HTML part from the same context. The PDF is
generated from its own template via xhtml2pdf — pure Python, because WeasyPrint
needs cairo and pango, which cannot be installed on the target host.

## Defect found and fixed

**Guest bookings could never receive their own confirmation.**

`POST /api/bookings/` validated `guest_email` — refusing the booking without one
— and then discarded it. The address was never written to the booking, so a
guest checkout produced a booking with no way to contact the customer. Every
confirmation, driver notification and cancellation for a guest would have gone
nowhere, silently.

Added `guest_email` and `guest_phone` to `Booking`, a `contact_email` property
that prefers the account address and falls back to the guest one, and the API
now stores what it validates.

## Failure containment

A mail failure must never break a booking — the payment has already gone through,
and losing the booking to save the notification is the wrong trade.

| Failure | Behaviour | Test |
|---|---|---|
| SMTP unreachable | Logged, returns False, no exception | `test_smtp_failure_is_logged_not_raised` |
| PDF rendering fails | Email still sends, without the attachment | `test_a_broken_pdf_still_sends_the_email` |
| Email switched off | Nothing sent, reason recorded | `test_disabled_email_sends_nothing_but_logs_why` |
| The confirmation call itself raises | **Booking stays confirmed** | `test_confirmation_failure_does_not_stop_a_payment` |

That last one is the one that matters: the webhook confirms the booking and
*then* emails. A test patches the mailer to raise and asserts the booking is
still `confirmed` afterwards.

## Decisions recorded

**A configurable email backend.** `ConfigurableEmailBackend` reads host and
credentials from the database on each connection, so changing mail hosts is a
dashboard action rather than a deployment. It falls back to Django settings when
nothing is configured, so development keeps working with the console backend.

**Every send is logged, success or failure.** Deliverability is the part of email
nobody can see. Without a log, "the customer says they never got the
confirmation" is unanswerable; with one, never-sent and sent-and-lost are at
least distinguishable.

**The encryption helper moved to `config/crypto.py`.** Two settings models now
hold secrets. Keeping the implementation in `payments/` would have meant
`notifications` importing from `payments` for something neither owns.

**The PDF is rendered from its own template, not the email's.** They share the
booking context, so they cannot disagree about the fare — the legacy system built
PDFs with a different library and a different layout, and the two drifted.

## Notes carried forward

- **Production SMTP has still never sent a real message.** The test button
  exists precisely for this; it needs running against the live mailbox before
  launch. Until then deliverability, SPF and DKIM are all unverified.
- The pickup reminder has no scheduler yet — that is the next item (cron
  management commands).

# Phase 13 QA Report — Scheduled Jobs

**Date:** 13 August 2026
**Status:** ✅ Passed — complete

---

## Exit criteria

| # | Criterion | Result |
|---|---|---|
| 1 | Pickup reminders sent on a schedule | ✅ `send_pickup_reminders` |
| 2 | Housekeeping for unbounded tables | ✅ `cleanup_stale_data` |
| 3 | Safe against cron double-firing and outages | ✅ tested |
| 4 | cPanel cron entries documented | ✅ `ops/crontab.example` |

## Automated results

```
pytest     370 passed  (18 scheduled), full suite including legacy replica
ruff       All checks passed!
rehearsal  REHEARSAL PASSED
```

## Why management commands rather than a queue

Shared hosting has no reliable long-running process, so Celery or an RQ worker
is not an option. cPanel does have cron, which is the only scheduler available.
Both commands are therefore written to survive how cron actually behaves: it
double-fires, it fires late after an outage, and occasionally two runs overlap.

## `send_pickup_reminders`

Emails customers whose pickup falls inside the window (24 hours by default).

**Deduplication uses `EmailLog`**, not a flag on the booking. A booking with a
*successful* `PICKUP_REMINDER` row is skipped, which gives two properties worth
having:

- running hourly is safe — each booking is caught once, as it enters the window
- a **failed** send is retried on the next run, because the dedupe keys on
  success rather than on attempt

Hourly is the right cadence, not daily: a booking made 20 hours before pickup
would never enter a once-a-day window.

| Condition | Behaviour |
|---|---|
| Pickup already passed | Skipped — after an outage it must not mail about yesterday |
| Cancelled booking | Skipped |
| No contact address | Skipped and counted in the output |
| Guest booking | Reminded at the guest address |
| Run twice | One email |
| SMTP failed last run | Retried |

## `cleanup_stale_data`

Weekly. **It never deletes a booking, a payment or a customer** — those are
business records and are kept indefinitely. A test asserts this directly.

| Target | Default retention | Why it grows |
|---|---|---|
| `WebhookEvent` | 90 days | One row per Stripe event, for replay protection |
| `EmailLog` | 180 days | One row per message sent |
| Unpaid bookings | 48h past pickup | Abandoned checkouts |

Abandoned bookings are **cancelled, not deleted**, and the transition writes a
`BookingStatusChange` with no user attached — so the audit trail shows plainly
that it was automated rather than someone's decision.

The query explicitly excludes anything with a successful payment. A booking left
`pending` while holding money is a bug somewhere else, and auto-closing it would
compound the problem rather than reveal it.

## Verified against real data

```
$ manage.py send_pickup_reminders --dry-run
within 24h: 2 · already reminded: 0 · no contact address: 0 · to send: 2
  would remind 732325 (Thu 13 Aug 15:00) -> donnastroy@gmail.com
  would remind 853591 (Thu 13 Aug 22:00) -> sharonkwoodul@gmail.com

$ manage.py cleanup_stale_data --dry-run
abandoned unpaid bookings : 3
  would abandon 257563 (pickup 24 Jun 2026 13:40)
  would abandon 885979 (pickup 23 Jun 2026 17:30)
  would abandon 148612 (pickup 22 Jun 2026 20:50)
```

**Worth flagging to the client:** those three are imported legacy bookings that
were left in `P` (pending) status with a pickup date now in the past. On the
first real run they will be marked cancelled. That is the correct reading of the
data — they were never paid and the date has gone — but it does change three
historical records, so it should not be a surprise.

## Deployment

`ops/crontab.example` holds the two entries, written to be pasted into
cPanel → Advanced → Cron Jobs **after** the Python app exists (the virtualenv
path does not exist before that).

```
0  * * * 0   send_pickup_reminders     hourly
15 3 * * 0   cleanup_stale_data        Sunday 03:15
```

Two notes captured there because they bite in practice:

- Run each once by hand with `--dry-run` before enabling the schedule.
- cPanel emails cron output to the account owner by default. The entries
  redirect to log files, but the "Email" field on the Cron Jobs screen must also
  be cleared, or the client receives an email every hour.

## Decisions recorded

**Bookings are never auto-completed.** A `confirmed` booking whose pickup has
passed is *probably* completed, but it might be a no-show or a cancellation
nobody recorded. Guessing would hide both. Staff mark completion on the dispatch
board.

**Cleanup defaults are conservative** — 90 and 180 days — and every threshold is
a command-line argument, so retention is a decision the client can change
without a code edit.

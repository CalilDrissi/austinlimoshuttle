# Phase 10 QA Report — Stripe Payments

**Date:** 13 August 2026
**Status:** ✅ Passed — complete end to end

---

## Exit criteria

| # | Criterion | Result |
|---|---|---|
| 1 | Credentials managed by an admin in the dashboard | ✅ Manager-only settings page |
| 2 | Secrets encrypted at rest, never rendered | ✅ |
| 3 | PaymentIntent creation | ✅ amount from the booking only |
| 4 | Webhook confirms bookings, signature-verified | ✅ |
| 5 | Refunds, attributed to the staff member | ✅ full and partial |
| 6 | Idempotent against replays | ✅ intent keys + event dedupe |

## Automated results

```
pytest    321 unit passed  (65 payments), 37 legacy-replica
ruff      All checks passed!
wheels    all 35 packages available as Linux wheels
```

## The checkout sequence

```
1.  POST /api/payments/intent/    -> client secret + publishable key
2.  Browser confirms with Stripe Elements
    (card details go customer -> Stripe; never through this server)
3.  Stripe POSTs /api/payments/webhook/  -> booking confirmed
```

**Step 3 is authoritative.** The browser's return from checkout is a hint, not
proof — it can be forged, and it simply does not arrive when a customer closes
the tab mid-redirect. The legacy system confirmed orders on the browser's word.

## Credentials

Managed at **Dashboard → Settings → Payments**, Manager-only.

| Property | How |
|---|---|
| Secret key at rest | Fernet-encrypted, key derived from `DJANGO_SECRET_KEY` |
| Secret key in the UI | Never rendered — `sk_test_••••9911` only |
| Form field | Write-only; blank submission keeps the stored value |
| Access | Dispatcher and Editor both get 403; the nav link is hidden |
| Audit | Records who changed it, when, and which fields |
| Publishable key | Stored plainly — it is designed to be public |

The form refuses **live mode with a test key** and **test mode with a live key**.
Both fail silently in production: the first takes no money while reporting
success, the second charges real cards during testing. It also catches a secret
key pasted into the publishable field.

## Security properties, and the tests that hold them

| Property | Test |
|---|---|
| The charged amount comes from the booking | `test_request_body_cannot_change_the_amount` — posting `amount: 1.00` still charges 14510 cents |
| An unsigned webhook cannot confirm a booking | `test_a_forged_success_cannot_confirm_a_booking` |
| A replayed webhook does not double-process | `test_replayed_event_is_ignored` |
| Only a last-4 is ever stored | `test_only_last4_is_stored_from_the_charge` |
| A customer cannot pay for another's booking | `test_another_customers_booking_is_404` |
| Misconfiguration does not leak details to customers | `test_misconfiguration_does_not_leak_details_to_the_customer` |
| Config endpoint exposes only the publishable key | `test_config_endpoint_exposes_only_the_publishable_key` |
| A Dispatcher cannot issue refunds | `test_dispatcher_cannot_refund` |

## Idempotency, at both layers

**Outbound.** `PaymentIntent.create` carries a stable idempotency key derived
from the booking reference and amount, so a retried request returns the same
intent rather than charging twice. A live intent is reused instead of stacking
up abandoned ones.

**Inbound.** A `WebhookEvent` row records every processed event id. Stripe
retries until it receives a 2xx and may deliver the same event more than once
regardless; without dedupe a retried `charge.refunded` records the refund twice
and the booking's financial history stops matching Stripe's. Processing happens
inside a transaction with the dedupe row, so a failure rolls both back and
Stripe's retry gets a genuine attempt.

## Refunds

Full and partial, from the booking detail page, Manager-only, always attributed
to the acting user. Refunding more than remains is refused. Refunds issued
directly in the Stripe dashboard are captured by the `charge.refunded` webhook,
so the two systems cannot silently disagree about what a customer was charged.

## Decisions recorded

**The client secret is not stored.** It is a short-lived credential for one
checkout; a column holding it is a column that can leak it. It is fetched from
Stripe when the checkout page needs it.

**CSRF exemption on the webhook is correct.** That endpoint authenticates by
HMAC signature over the raw body, which is stronger than a CSRF token and is the
only thing it trusts. A test asserts an unsigned request is refused.

**Configuration errors return 503, not 400.** For the webhook this makes Stripe
retry once the secret is configured, rather than discarding the event. For the
customer it produces a neutral "unavailable right now" while the operator detail
goes to the log.

**Unhandled event types return 200.** Acknowledging an event we deliberately
ignore stops Stripe retrying it indefinitely.

**Credentials are read per call, not cached at import.** Changing them in the
settings page takes effect immediately, with no restart.

## Operational notes for the runbook

- **Rotating `DJANGO_SECRET_KEY` makes the stored Stripe keys unreadable** and
  they must be re-entered. `decrypt()` returns `None` rather than raising, so
  this degrades to "not configured" instead of a 500 on every page.
- The webhook endpoint must be registered in Stripe (Developers → Webhooks) and
  its signing secret pasted into the settings page. The URL is displayed on that
  page. Required events: `payment_intent.succeeded`,
  `payment_intent.payment_failed`, `charge.refunded`.
- Until the webhook secret is set, incoming events are refused with 503 and
  bookings will never confirm.

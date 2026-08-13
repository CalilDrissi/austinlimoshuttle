# Phase 6 QA Report — REST API

**Date:** 12 August 2026
**Status:** ✅ Passed — exit criteria met

---

## Exit criteria

| # | Criterion | Result |
|---|---|---|
| 1 | Endpoints per the build brief | ✅ 13 routes |
| 2 | No endpoint trusts a client-supplied amount | ✅ structurally impossible |
| 3 | Tampered and expired quotes rejected | ✅ tested |
| 4 | A customer cannot read another's booking | ✅ tested |
| 5 | Throttling on auth, quote and enquiry endpoints | ✅ |

## Automated results

```
pytest    219 unit passed (28 API), 37 legacy-replica
ruff      All checks passed!
```

## Endpoints

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/pages/` · `/api/pages/<slug>/` | — | Unpublished pages 404 |
| GET | `/api/vehicles/` | — | Active only |
| GET | `/api/availability/` | — | Blackout dates + surcharge windows |
| POST | `/api/quotes/` | — | Prices every vehicle, returns signed tokens. 30/hr |
| POST | `/api/bookings/` | optional | Redeems a token; guest checkout supported |
| GET | `/api/account/bookings/` | session | The caller's own bookings only |
| GET/PATCH | `/api/account/bookings/<ref>/` | session | Read; `action: cancel` |
| POST | `/api/auth/login/` · `logout/` · `register/` | — | Throttled |
| GET | `/api/auth/me/` | session | |
| POST | `/api/enquiries/` | — | 10/hr |

## The price-integrity design

The browser never sends a price, and cannot: `BookingCreateSerializer` has no
money field at all, so an amount is not merely ignored — it is inexpressible.
Booking presents a **signed, short-lived quote token**; the server unpacks the
journey and **recomputes the fare** before storing anything.

Tested behaviours:

| Attack | Result |
|---|---|
| Post `total: 1.00` alongside a valid token | Booking stored at **145.10** |
| Alter the token's signature | 400, no booking created |
| Reuse a token after its TTL | 400 "expired", no booking |
| Omit the token | 400 |
| Rates change between quote and booking | Fare **recomputed**, not replayed |

That last one matters both ways: a customer cannot lock in a stale price, and
the business cannot accidentally honour one.

## Authorisation

Legacy exposed `direct-payment.php?orderID=` with no authentication, which made
the whole orders table readable. The replacement:

- Booking lookups are scoped to `customer=request.user`.
- Another customer's reference returns **404, not 403** — a 403 would confirm
  the reference exists, which is enough to enumerate bookings.
- Anonymous access to account endpoints returns 401/403.
- Login failures give one message whether the address is unknown or the password
  is wrong, so the endpoint cannot be used to enumerate registered customers.
- Registering an already-registered address returns a neutral 202 for the same
  reason.

## Defects found and fixed

**Money was serialized as JSON floats.** `145.10` came back as `145.1`, and
anything a client computed from it would inherit binary rounding error. JSON has
no decimal type, so every monetary value now crosses the boundary as a
fixed-precision **string**. Caught by a test asserting the exact string.

**A test compared times in the wrong timezone.** It set hour 23 on a UTC
datetime, which is 18:00 in Austin, so the late-night surcharge correctly did
not apply and the test failed. The test was wrong, not the engine — fixed to
build 23:00 Austin local. Worth recording because it is exactly the confusion
the engine's own local-time test exists to prevent.

## Decisions recorded

**Quote tokens are signed, not encrypted.** They carry nothing secret — only
values the customer supplied. Signing makes them tamper-evident; the TTL makes
them perishable. Encryption would add key management for no benefit.

**Guest checkout is supported.** The legacy funnel forced registration before
payment. `customer` is nullable, so a guest booking is a first-class record.

**Cancellation is the only PATCH action.** Anything else (changing pickup time,
vehicle, address) reprices the journey and belongs in a fresh quote.

## Notes carried forward

- Stripe is out of scope for this build. `POST /api/bookings/` leaves the
  booking `pending`; the payment step is the next piece of work.
- Password reset endpoints are not implemented. They are required at launch —
  all 1,251 imported accounts need a reset before they can sign in.

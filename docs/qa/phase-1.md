# Phase 1 QA Report — Accounts, Fleet, Pricing + Import

**Date:** 12 August 2026
**Status:** ✅ Passed — exit criteria met

---

## Exit criteria

| # | Criterion | Result |
|---|---|---|
| 1 | Counts reconcile with legacy | ✅ 1,251 users, 7 vehicles, 11 blackout dates, 1 surcharge |
| 2 | Re-running imports changes nothing | ✅ idempotency asserted per importer |
| 3 | Rate card matches legacy row-for-row | ✅ verified against `limousin_car_list` |
| 4 | No password can be imported | ✅ 0 of 1,251 accounts have a usable password |

## Automated results

```
pytest    107 passed (94 unit + 13 legacy-replica)
ruff      All checks passed!
check     System check identified no issues
```

## Import results

```
Fleet:   7 created, 0 updated, 1 skipped   (8 legacy rows)
Pricing: 12 created, 1 updated, 0 skipped  (13 legacy rows)
Members: 1250 created, 1 updated, 0 skipped (1251 legacy rows)
```

| Check | Result |
|---|---|
| Customers imported | ✅ 1,251 |
| Customers with a usable password | ✅ **0** |
| Emails normalised to lowercase | ✅ no uppercase remains |
| Vehicles / active | ✅ 7 / 4 |
| Distance bands generated | ✅ 20 (bands contiguous, no gaps or overlaps) |
| Blackout dates | ✅ 11 (SXSW +40%, F1 +80%) |
| Late-night surcharge | ✅ 21:00→06:00, +20%, crosses midnight |
| Admin screens render | ✅ 8/8 HTTP 200 |

### Rate cards as imported

| Vehicle | Hourly | Min fare | 0–6 mi | 6–50 mi | 50–100 mi | 100+ mi |
|---|---|---|---|---|---|---|
| Business Class | $85 | $95 | $15.00 | $2.90 | $2.20 | $1.50 |
| Business SUV | $125 | $105 | $20.00 | $4.00 | $3.50 | $2.50 |
| Mercedes Sprinter | $125 | $250 | $41.66 | $5.00 | $4.00 | $3.00 |

## Legacy data issues surfaced

**Chrysler 300 Limousine is active but cannot be quoted.** `status='Y'` with
every rate at zero — no per-mile bands and no hourly rate. On the legacy site it
would quote $0.00 for any journey. The importer refuses to create zero-rate
bands (which would let it quote nothing) and reports it as an exception instead.
**The client should confirm whether this vehicle should be deactivated or given
rates.**

**The late-night window in the admin did not match the code.**
`limousin_special_time_rate.title` reads *"For early pickup, 12 am to 6 am. For
late pickup, from 9 pm to 11.59 pm"* while `pickup_details.php:335` implements
`time < 06:00:00 || time > 21:00:00`. These describe the same window, so no
pricing change results — but the prose was decorative and the real rule was
hardcoded. The import takes its times from the PHP and preserves the sentence
only for traceability.

## Defects found and fixed

**1. Mojibake regex was invalid and crashed every importer.**
`[\x80-\xbf€-ÿ]` looks like a character range but runs from U+20AC down to
U+00FF; Python's `re` rejects it with `bad character range`. All three import
commands aborted on import of the module. Rewritten with explicit escapes and
covered by tests.

**2. cp1252 text was left damaged.**
The first repair pass only handled UTF-8 misread as latin1. Legacy content was
edited through a Windows WYSIWYG, so smart quotes were also written as single
cp1252 bytes (`0x92` for `'`), which are undefined in latin1 and are not valid
UTF-8 — the conservative path left them as raw control characters in
customer-facing copy. A cp1252 fallback now handles them, applied only when the
UTF-8 interpretation fails.

## Decisions recorded

**Surcharge bounds are exclusive at both ends**, matching legacy exactly. A
pickup at 21:00:00 is *not* surcharged because the old condition was
`> 21:00:00`. Tests pin both boundaries; changing either would silently reprice
bookings.

**Blackout and late-night percentages are additive.** Legacy computes
`increase_amount = blackout% + late_night%` and applies the sum once
(`pickup_details.php:331-340`). Applying them sequentially would over-charge —
a 40% SXSW date at 22:00 is +60%, not +68%.

**Distance bands are validated as a set, not individually.** The admin formset
rejects gaps, overlaps, a first band not starting at 0, and anything other than
exactly one unbounded final band. A gap means miles charged at zero; an overlap
means the first match silently wins. Neither is detectable from a single row.

**Vehicles with no rates get no bands.** Creating zero-rate bands would let a
vehicle quote $0.00 for a real journey — reporting it as an exception is safer
than silently pricing nothing.

## Notes carried forward

- Chrysler 300 Limousine needs a client decision (deactivate, or supply rates).
- Legacy `plan_*` subscription columns and `hundred` remain unread; confirm they
  are empty before Phase 8 so they can be formally dropped from scope.

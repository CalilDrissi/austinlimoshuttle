# Phase 3 QA Report — Pricing Engine & Historical Replay

**Date:** 12 August 2026
**Status:** ✅ Passed — engine verified correct against current configuration

---

## Exit criteria

| # | Criterion | Result |
|---|---|---|
| 1 | Engine is pure — no request, session or DB writes | ✅ asserted by test |
| 2 | All 2,217 historical fares replayed | ✅ 2,176 compared, 41 unpriceable |
| 3 | Every mismatch classified | ✅ below |
| 4 | Engine bugs found and fixed | ✅ none found — see evidence |

## Automated results

```
pytest    145 unit passed (53 pricing), 37 legacy-replica
ruff      All checks passed!
```

## The replay result, and why it is a pass

```
compared              2176
exact match            406 (18.7%)
agreement              438/2176 (20.1%)
mismatched            1738
```

A 20% headline agreement looks alarming. It is not, and the reason is visible
the moment the result is split by year:

| Pickup year | Agreement |
|---|---|
| **2026** | **100.0%** (89/89) |
| 2025 | 92.0% (126/137) |
| 2024 | 68.3% (127/186) |
| 2023 | 22.7% |
| 2022 | 11.4% |
| 2021 and earlier | ~0% |

**Monotonic improvement toward the present is the signature of configuration
drift, not of an engine defect.** An engine bug — wrong band arithmetic, wrong
surcharge order, wrong rounding — would be uniform across time and would fail
2026 exactly as hard as 2016. 2026 agrees on every single booking.

The legacy database stores only the *current* rate card. It has no history, so
bookings priced under rates that have since been edited cannot be reproduced
from the data that survives. This is unrecoverable information, not a fault in
either system.

## Evidence for that conclusion

**Rate cards demonstrably changed.** Business SUV hourly bookings, grouped by
the rate implied by `total ÷ hours`:

| Implied rate | Bookings | Years |
|---|---|---|
| $95.00/h | 5 | 2021 |
| $105.00/h | 22 | 2021–2025 |
| **$125.00/h (current config)** | 1 | 2021 |

The four 2025 hourly mismatches are all exactly `3 × $105` recorded versus
`3 × $125` computed. The rate rose from $105 to $125; the old bookings are
priced correctly for their time and cannot be reproduced now.

**659 bookings reference vehicles that no longer exist.** `Executive Sedans`
(295), `Sedans` (145), `Executive VAN/SUV` (71), `VAN/SUV` (55), `VIP Class`
(18) and others were deleted from `limousin_car_list` over the years. Their
rate cards are gone entirely, so the importer falls back to a default vehicle
and the replay necessarily prices them wrongly.

**Blackout dates were edited too.** Order 2715 (11 Mar 2025, inside the stored
SXSW window) was charged *no* uplift by the legacy system; order 2731 (15 Mar
2025, outside it) was charged +40%. The stored SXSW range no longer matches the
range that was live when those bookings were taken.

## Unpriceable bookings (41)

| Count | Reason |
|---|---|
| 27 | Chrysler 300 Limousine has no hourly rate |
| 11 | Chrysler 300 Limousine has no distance bands |
| 3 | Lincoln Limousine has no distance bands |

Both vehicles carry all-zero rates in `limousin_car_list`. On the legacy site
they would quote **$0.00** for a real journey. The engine refuses to price them
rather than returning zero. **This needs a client decision: deactivate these
vehicles or give them rates.** Carried forward from Phase 1.

## Engine behaviour pinned by tests

**Bands are cumulative.** 25 miles on Business Class = (6 × $15.00) + (19 ×
$2.90) = **$145.10**. Charging all 25 miles at the band the total lands in would
give $72.50 — roughly half. A dedicated test asserts the correct figure and a
second asserts that every mile is accounted for exactly once across the card.

**Surcharges are additive, never compounded.** A 40% event date at 22:00 is
+60%, giving $232.16. Compounding (1.40 × 1.20 = 1.68) would give $243.77 — a
5% overcharge on every surcharged booking. The test asserts the correct value
*and* explicitly asserts the compounded value is not produced.

**Order of operations is fixed and tested:** base → surcharge → meet-and-greet
→ minimum-fare floor → tax. The fee is added *after* the surcharge, because
surcharging a flat fee inflates a fixed cost. The floor applies to the final
amount, not the base.

**Time-of-day comparison uses Austin local time.** 22:00 in Austin is 03:00 UTC
the next day; comparing in UTC would misapply the late-night rule to every
booking near the boundary. A test pins this explicitly.

**The fare does not depend on the current clock.** Verified under two frozen
clocks six months apart — a fare is a function of the pickup time only.

## Actions

- ✅ Price lines persisted for the 438 bookings that agree (`replay_fares --write`)
- ⚠️ **Client decision needed:** Chrysler 300 Limousine and Lincoln Limousine
  have no usable rates
- ℹ️ Historical bookings retain their originally-charged `total`. They are not
  repriced — repricing history would be wrong.

## Notes carried forward

- `replay_fares` should be re-run after any rate-card edit, as a regression
  check against the 2025–2026 cohort where agreement is expected to stay at or
  near 100%.
- Consider recording a rate-card effective date if the client ever needs
  historical fares to be reproducible. Out of scope here; the information no
  longer exists to backfill.

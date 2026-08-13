# Phase 2 QA Report — Bookings & Order Import

**Date:** 12 August 2026
**Status:** ✅ Passed — exit criteria met

---

## Exit criteria

| # | Criterion | Result |
|---|---|---|
| 1 | 2,217 bookings imported | ✅ |
| 2 | Every booking resolves to a vehicle and customer, or is listed as an exception | ✅ 2,217 vehicles / 2,214 customers, 3 documented |
| 3 | Revenue matches legacy to the cent | ✅ $312,886.32 both sides |
| 4 | Zero card/CVV patterns in the new database | ✅ |
| 5 | Reconciliation table produced, exceptions documented | ✅ below |

## Automated results

```
pytest    151 passed  (114 unit + 37 legacy-replica)
ruff      All checks passed!
```

## Reconciliation

| Measure | Legacy | Imported | Match |
|---|---|---|---|
| Bookings | 2,217 | 2,217 | ✅ |
| Revenue | $312,886.32 | $312,886.32 | ✅ |
| Completed (`D`) | 2,056 | 2,056 | ✅ |
| Cancelled (`C` + `DL`) | 149 + 3 | 152 | ✅ |
| Pending (`P`) | 9 | 9 | ✅ |
| Transfers (have distance) | 2,131 | 2,131 | ✅ |
| Hourly hires | 86 | 86 | ✅ |
| Payment records | 2,217 matched | 2,217 | ✅ |
| Drivers (from free text) | — | 40 | new |

**Date round-trip spot check.** Legacy order 494 reads
`Mon, 11 Jan 2016, 5:00 AM`; stored as an aware UTC datetime and rendered back
in `America/Chicago` it is `Mon, 11 Jan 2016, 5:00 AM`. Identical.

**Cardholder data.** 0 payments carry a card brand or last-4 — nothing was
available to import, which is correct. `test_importer_never_selects_card_columns`
asserts the strongest form of this: the SQL cannot return what it never asks for.

## Exceptions (documented, not silently dropped)

**271 orphaned `limousin_orderdetails` rows.** They reference `order_id` values
between 23 and 493, but `limousin_order` starts at id 494. The legacy system
deleted bookings and left their payment rows behind. This is exactly the
2,488 − 2,217 = 271 gap. The importer reports each one and refuses to invent a
booking. **No action needed — the data is genuinely gone.**

**3 bookings with no customer.** Their `member_id` does not match any surviving
`limousin_member` row. Retained as guest bookings.

**2 duplicate `orderNum` values + 1 blank.** `orderNum` is not unique in legacy
(`84954` and `522345` each appear twice). Since `reference` is unique here,
collisions get the legacy id appended (`84954-2806`), keeping the customer-facing
code recognisable and traceable rather than dropping the booking.

## Defects found and fixed

**1. PyMySQL could not read the legacy tables at all.**
PyMySQL maps MySQL's `latin1` onto Python's **cp1252** codec, following MySQL's
own convention. But cp1252 leaves `0x81`, `0x8d`, `0x8f`, `0x90` and `0x9d`
undefined — and those bytes occur in precisely the damaged rows the repair pass
exists to fix. Every read raised `UnicodeDecodeError`.

Fixed by overriding `conn.encoding = "latin-1"`, which maps every byte
0x00–0xFF onto the code point of the same value and loses nothing.
`use_unicode=False` was tried first and rejected: raw bytes break PyMySQL's
`DECIMAL` and `DATE` converters.

**2. Historical bookings all claimed to have been created today.**
`created_at` is `auto_now_add`, which ignores any supplied value on insert. Now
set explicitly with a follow-up `UPDATE`, so nine years of booking history keeps
its real timeline.

**3. Reference collisions aborted the whole import.**
The first run died on `Duplicate entry '84954' for key 'reference'`. Handled as
described above.

## Decisions recorded

**`DL` ("deleted") maps to cancelled, not to deletion.** Three bookings carry it.
Destroying records that the legacy system merely flagged would lose financial
history; they are cancelled and retained.

**Guest bookings are supported at the schema level.** `customer` is nullable
with `SET_NULL`, so deleting an account never erases booking or revenue history.

**Vehicle deletion is blocked by `PROTECT`.** A vehicle with bookings can be
deactivated, never deleted — otherwise renaming the fleet rewrites history.
`vehicle_name_snapshot` additionally preserves the name as sold.

**Payments cannot be created through the admin.** `has_add_permission` returns
False: payment state is owned by the provider, not by staff typing rows. Refunds
are the single writable action and record who issued them.

## Notes carried forward

- The legacy-replica test suite takes ~6.5 minutes because several tests run
  full imports. Consider a session-scoped fixture if it becomes a nuisance;
  `-m "not legacy"` runs the 114 unit tests in ~4 seconds.
- Fare fields are populated from the legacy `price` only. Phase 3 recomputes
  them through the pricing engine and reconciles the two.

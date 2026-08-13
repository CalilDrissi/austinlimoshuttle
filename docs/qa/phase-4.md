# Phase 4 QA Report — Content & Enquiries

**Date:** 12 August 2026
**Status:** ✅ Passed — exit criteria met

---

## Exit criteria

| # | Criterion | Result |
|---|---|---|
| 1 | Pages import with SEO metadata | ✅ 17 pages |
| 2 | Slugs preserved byte-identically | ✅ including the malformed ones |
| 3 | Enquiries merged from three tables | ✅ 928 |
| 4 | Zero double-encoding in a full-table scan | ✅ 0 of 17 |

## Automated results

```
pytest    161 unit passed, 37 legacy-replica
ruff      All checks passed!
```

## Import results

```
Content: 970 rows processed, 25 skipped
```

| Entity | Count |
|---|---|
| Pages | 17 |
| Banners | 7 |
| Testimonials | 3 |
| Gallery images | 14 |
| Enquiries | 928 (917 general, 8 service, 3 corporate) |

**Mojibake repair, verified on real content:**

```
LEGACY   : 'ay when youâ\x80\x99re looking for a'
REPAIRED : 'ay when you’re looking for a q'
```

Full-table scan: **3 legacy rows carried damage, 0 imported pages do.**

**Slug preservation** — spot-checked and present: `austin-airport-car-service`,
`wedding-limousine-services`, `fleet`, `contact-us`, and the malformed
`wwwaustinlimoshuttlecom`.

## Correction to an earlier figure

**The "29 of 36 pages are damaged" figure in `legacy-app-brief.html` and
`new-build-brief.html` was wrong. The true number is 3 of 36.**

The original count came from `... WHERE desc LIKE '%â%'` run through the MySQL
client. The legacy database collates as `latin1_swedish_ci`, which is
**accent-insensitive** — so `â` matched plain `a`, and the query counted every
row containing the letter *a*. Re-scanning the raw bytes for C1 control
characters (the actual fingerprint of misdecoded UTF-8) finds 3 affected rows.

This makes the encoding problem smaller than reported, not larger. The repair
pass and its tests are unchanged and still necessary — the damage is real, just
narrower. Both client documents have been corrected.

## Skipped rows (25, all intentional)

| Count | Reason |
|---|---|
| 8 | Template does not exist (`login.php`, `lead_driver.php`, `confirm_driver_details.php`, `cancel_transaction.php`, `contributor.php`, `edit_dashboard.php`, `login-or-register.php`, `add_driver_details.php`) — these routes are already broken on the live site |
| 11 | Funnel and account pages (`payment.php`, `pickup_details.php`, `thankyou.php`, …) — routing belongs to the frontend now, so they are not content |
| 6 | Enquiries with an unusable email address |

## Defects found and fixed

**MariaDB silently discarded a uniqueness guard.**
`UniqueConstraint(..., condition=Q(legacy_row_id__isnull=False))` compiles to a
partial index, which MariaDB does not support — so Django dropped it and the
duplicate-import guard did not exist. Caught because the test asserting it
failed.

Replaced with a plain `UniqueConstraint`, which gives the same behaviour on this
backend for a different reason: MySQL and MariaDB treat NULLs as distinct in a
unique index, so website-created enquiries (`legacy_row_id IS NULL`) stay
unconstrained while imported rows cannot duplicate. Verified present in the
database (`SHOW INDEX` reports `Non_unique 0`).

**Legacy zero-dates crashed the import.**
`limousin_corporate_account.post_date` is a varchar, not a timestamp, and holds
MySQL zero-dates (`0000-00-00`) which `datetime` rejects with
`year 0 is out of range`. Now parsed defensively; unusable values fall back to
the import time rather than failing the run.

## Decisions recorded

**The repair runs on import, not as a database charset conversion.** Converting
`latin1 → utf8mb4` in place would store the mojibake permanently as valid UTF-8,
at which point the original characters are unrecoverable.

**Funnel pages are not content.** Legacy used `limousin_cms` as its router, so
`payment.php` and `pickup_details.php` were rows in the CMS table. They are not
imported: the frontend owns routing now.

**Corporate applications become enquiries.** Legacy captured three in nine years
and never connected them to billing, so they are records of interest with a
`nature` discriminator, not a billing entity.

# Phase 9 QA Report — Server-Side Distance Lookup

**Date:** 13 August 2026
**Status:** ✅ Passed — vulnerability closed

---

## What this fixed

`/api/quotes/` accepted `distance_miles` from the browser and never verified it.

The signed quote token protected the *price* from tampering, but it signed a
distance the customer supplied. A 40-mile airport run posted as
`distance_miles: 1` produced a legitimately signed quote at the **$95 minimum
fare**, and every downstream check passed — signature valid, server-side
recomputation performed, booking created. The server faithfully recomputed the
wrong answer.

The price-integrity layer was built correctly and then fed untrusted input.

## The fix

`pricing/distance.py` measures every transfer from its two addresses via the
Google Distance Matrix API. `QuoteRequestSerializer` no longer has a
`distance_miles` field at all, so a distance cannot be expressed by a client any
more than a price can.

**Failures are hard failures.** There is deliberately no fallback to a
client-supplied value — a fallback is the same vulnerability behind a retry:
anyone wanting the cheap fare need only make the lookup fail. A failed
measurement returns 422 and produces no quote.

## Automated results

```
pytest    293 passed  (256 unit + 37 legacy-replica)
ruff      All checks passed!
wheels    all 33 packages available as Linux wheels
```

18 new distance tests, 4 new API tests. Every test stubs the HTTP call — the
suite never touches the network or spends the client's Google billing.

| Test | Asserts |
|---|---|
| `test_a_client_supplied_distance_is_ignored` | Posting `distance_miles: 1` still yields the measured 25-mile fare of $145.10 |
| `test_lookup_failure_fails_the_quote` | 422, no quote, no fallback |
| `test_failure_is_not_cached` | A transient timeout does not poison the cache for a week |
| `test_does_not_parse_the_display_string` | Uses the metre value, not `"11.3 mi"` |
| `test_missing_key_fails_loudly_without_calling_the_api` | No silent degradation |

## Live verification

Real key, real API, from this machine:

```
Austin-Bergstrom International Airport → Downtown Austin, TX
11.336 mi | 18 min
resolved: Austin-Bergstrom International Airport (AUS)
```

## Decisions recorded

**Distance comes from `distance.value` (metres), not `distance.text`.** The text
is rounded for humans and locale-dependent; `"11.3 mi"` would lose precision on
a fare that multiplies by a per-mile rate. A test asserts the metre value wins
even when the two disagree.

**Results cache for a week.** The airport-to-downtown pair is requested
constantly and each call is billable. Cache keys normalise case and whitespace,
so `"  abia  "` and `"ABIA"` share an entry. Failures are never cached.

**Production uses a database-backed cache.** Passenger may run several worker
processes, and a per-process cache would issue duplicate billable lookups.
Requires `manage.py createcachetable` at deploy — added to the runbook.

**`requests` is now a direct dependency.** It arrived transitively via
xhtml2pdf; depending on it directly while declaring it nowhere is how a
dependency disappears in a future upgrade.

## Carried forward — the API key

The key came from the legacy site's source (`AIzaSyBNo2…`), as instructed. Two
things the client should know:

**It has been in public client-side JavaScript for nine years.** Anyone who
viewed the page source has it. It is not a secret and should be treated as
compromised.

**It appears to be unrestricted.** It works from this machine with no HTTP
referrer, which is what makes it usable server-side — but it also means anyone
who scraped it can bill Google against the client's account.

Recommended before launch: create a **new key restricted to the server's IP**,
enabled only for Distance Matrix, and delete the old one. That is a client
action in the Google Cloud console; nothing in our code changes except the value
in `.env`. Not urgent for local development, and it does not block the build.

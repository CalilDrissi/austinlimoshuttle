# Phase 5 QA Report — Staff Dashboard

**Date:** 12 August 2026
**Status:** ✅ Passed — exit criteria met

---

## Exit criteria

| # | Criterion | Result |
|---|---|---|
| 1 | Dispatch board, booking list/detail, enquiries inbox | ✅ built |
| 2 | Role groups with a tested permission matrix | ✅ Dispatcher / Manager / Editor |
| 3 | Every status change writes an audit row naming the user | ✅ |
| 4 | Simulated operating day completes without Django admin | ✅ |

## Automated results

```
pytest    191 unit passed (30 dashboard), 37 legacy-replica
ruff      All checks passed!
check     System check identified no issues
```

## Screens

| Screen | URL | Purpose |
|---|---|---|
| Overview | `/dashboard/` | Six counters — pickups today, next 7 days, unassigned drivers, awaiting payment, unread enquiries, week's revenue — plus the next 8 pickups |
| Dispatch board | `/dashboard/dispatch/` | Next 48 hours in pickup order; driver and status changed inline, no page hop |
| Bookings | `/dashboard/bookings/` | Search by reference, name, address, flight; filter by status and date range; CSV export |
| Booking detail | `/dashboard/bookings/<ref>/` | Journey, customer, itemised fare, payments, update form, full status history |
| Enquiries | `/dashboard/enquiries/` | Inbox filtered by unread/unanswered/type |
| Enquiry detail | `/dashboard/enquiries/<id>/` | Message, reply form; opening marks it read |

Legacy had 32 admin files, of which 8 never worked and 5 duplicated CMS editing.
This is 6 purpose-built screens plus Django's generated admin for plain CRUD.

## Permission matrix (tested)

| Capability | Dispatcher | Manager | Editor |
|---|---|---|---|
| View / change bookings | ✅ | ✅ | ❌ |
| Assign drivers, change status | ✅ | ✅ | ❌ |
| Change vehicle rates | ❌ | ✅ | ❌ |
| Surcharges, blackout dates | ❌ | ✅ | ❌ |
| Issue refunds | ❌ | ✅ | ❌ |
| Edit content, banners, testimonials | ❌ | ❌ | ✅ |
| Reach the dashboard at all | ✅ | ✅ | partial |

Permissions granted: Dispatcher 13, Manager 40, Editor 18.

Tests assert the negative cases explicitly — an Editor gets **403** on the
bookings list, and a customer account is refused every screen. Access control
that is only tested positively is not tested.

## Manual QA — simulated operating day

| Step | Result |
|---|---|
| Sign in as Dispatcher | ✅ |
| Overview shows correct counters | ✅ |
| Dispatch board lists next 48 h in pickup order | ✅ |
| Assign a driver inline | ✅ persisted |
| Change status to Completed with a note | ✅ audit row written |
| Cancel a booking with a reason | ✅ `cancelled_at` and reason stamped |
| Search bookings by reference | ✅ matches only that booking |
| Export CSV | ✅ correct headers, no card columns |
| Open an enquiry | ✅ auto-marked read |
| Record a reply | ✅ attributed to the acting user |
| Sign in as Editor, try bookings | ✅ 403 |

## Decisions recorded

**Roles are defined in code, not clicked into a UI.** `dashboard/permissions.py`
holds the matrix and `manage.py sync_roles` applies it idempotently. Permissions
therefore go through code review and can be re-applied on every deploy, rather
than drifting silently in a database nobody audits.

**Every status transition writes `BookingStatusChange` with the acting user.**
This is the direct answer to the legacy single shared admin account, where no
action could be attributed to anyone. A no-op save deliberately writes nothing.

**The status field is validated against the enum.** Posting an arbitrary string
is rejected and leaves both the booking and the audit trail untouched — tested.

**The dispatch board covers 48 hours, not everything.** It answers "what is
happening next and does it have a driver". Anything longer belongs in the
booking list with its filters.

**Booking lists cap at 50 rows with the total shown.** A silent cap reads as
"that's all there is"; the count and a pointer to CSV export make the truncation
visible.

**CSV export is asserted to contain no card columns.** The header row is checked
for `card`, `cvv`, `expiry` and `security` — a regression here would re-export
exactly the data this project exists to remove.

## Notes carried forward

- Pagination is a hard cap rather than paged navigation. Adequate at ~250
  bookings a year; revisit if the dataset grows.
- The dashboard reuses Django's admin login rather than a bespoke sign-in page.
  Fine for staff; worth revisiting only if the client wants branding there.

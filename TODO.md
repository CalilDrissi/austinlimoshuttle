# TODO

Carried-forward work. `outstanding-notes.html` holds the client-facing version;
this file is for the build.

## Next up

### Lock down `/admin/`

The client must never need Django's admin, and now does not: all ten managed
areas live in the dashboard. What remains is making that true in access terms
rather than only in the navigation.

**What is done**

- Every model that required the admin has a dashboard screen — drivers,
  vehicles and rate cards, surcharges, event dates, pages, testimonials,
  banners, gallery, staff accounts, customers, plus the tax and site-detail
  settings screens.
- `/admin/login/` redirects to the branded gate, so the admin's own sign-in
  screen is unreachable.
- The Django admin link is hidden from the sidebar for non-superusers.
- The Manager role carries all 63 permissions the dashboard needs.

**What is left**

1. Demote `admin@austinlimoshuttle.com` from superuser to staff + Manager.
   It is the client's account and is currently a superuser, so it can reach
   `/admin/` by typing the URL.
2. Restrict `/admin/` to superusers — Django's `AdminSite` admits any
   `is_staff` account by default, so a Dispatcher could otherwise walk in.
3. Verify a Manager can still reach every dashboard screen afterwards. This is
   the step that matters: demoting without checking would lock the client out
   of work they need, which is worse than the problem being solved.

**Why hiding the link was not enough:** navigation is not access control. The
account can still type the address, and the admin has no set-level validation
on a rate card — a gap between distance bands there would misprice every future
quote silently.

## Deferred

### Memory / knowledge tooling for working with Claude Code

Scheduled **after the frontend is chosen and introduced** — deliberately, so the
tooling is set up against the codebase we are actually going to have rather than
the one we have today.

**Do these first, in this order:**

1. **`CLAUDE.md` at the project root.** The rules that apply every session.
   Everything below is optional; this is not. Seed it with what has already cost
   time more than once:
   - The local Django server runs with `--noreload`; code changes need a restart
   - Tests need `-m "not legacy"` unless the sanitised replica is loaded
   - The CSP sets `script-src 'self'` — an inline `<script>` is dropped by the
     browser with no server-side error, so the page looks perfect and simply
     does not work
   - Local MariaDB is on port 3307 via Docker, not 3306
   - `curl` gets a 406 from the live site; mod_security wants a browser
     user-agent
   - `DJANGO_STATIC_ROOT` defaults to the *live site's* web root and must be
     overridden
   - Deploy is rsync → `collectstatic` → `touch tmp/restart.txt`, because the
     cPanel `passengerapps` feature is disabled on the account
2. **A `/deploy` skill** encoding that deploy sequence, so it runs the same way
   every time instead of living in one conversation's context.
3. **A production-guard hook** in `settings.json`. "Never touch production" is
   currently enforced by instruction; a `PreToolUse` hook enforces it in the
   harness, which is the difference between a rule and a guarantee.

**Then, if it still feels thin:**

- **Cognee** — the strongest fit if we add one. The only option with a code-graph
  pipeline rather than chat memory, and it speaks MCP so Claude Code uses it
  natively. Worth it mainly if memory is shared across several agents/clients
  rather than this one project.
- **Zep (Graphiti)** — the runner-up, for one reason specific to this project:
  its bi-temporal model records *when* a fact was true. Rate cards drifted over
  nine years, the two databases diverged on a known date, and "what did we
  believe in March" is a real question here.
- Mem0 (fastest, vector, general-purpose) and Letta (MemGPT lineage, agent
  rewrites its own memory) are the other serious options; neither is shaped for
  this job.

**Two cautions carried forward:** much of the "top 10 memory tools" writing is
vendor SEO — several vendors rank their own pages for the comparison query — and
vendor benchmarks do not reproduce under independent harnesses. Claude Code also
already ships `CLAUDE.md` plus file-based auto memory, so a third-party layer has
to beat those, not merely exist.

## Also outstanding

- **No public website.** `/` is a 404. The customer-facing site does not exist;
  the legacy PHP site is still taking real bookings on the main domain.
- **Catch-up import.** The two databases have diverged since 14 August 2026.
  Whatever the legacy site records from then on is not in the new one, and a
  cutover will need those rows.
- **Email and cron are off, deliberately.** `send_pickup_reminders` mails real
  customers about upcoming pickups; enabling it against imported data would
  email real people about a system that is not live.
- **Stripe is not configured** on production. Nothing can charge a card. Set
  test keys first and confirm the webhook reaches `/api/payments/webhook/`.
- **Ask InMotion to enable `passengerapps`.** The account's cPanel feature flag
  is off, so the app is wired to Passenger through a hand-written `.htaccess`.
  It works, but the cPanel screen for restarting it is unavailable.
- **`public_html` still serves `admin.zip`, `backup_download.zip` and
  `backupsite20.03.2017/`.** Predates this work and is how the legacy admin
  source and Stripe key leaked — see `security-issue.html`. A one-command fix,
  but it touches the live site, so it needs the client's go-ahead.
- **Two vehicles cannot be priced** — Chrysler 300 Limousine and Lincoln
  Limousine have all-zero rates from the legacy data. Needs a client decision:
  deactivate, or supply rates.
- **Customers migrated without passwords.** All 1,251 must use the reset link
  before their first sign-in. Needs saying at launch or it reads as a breach.

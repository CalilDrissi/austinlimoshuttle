# Frontend Plan — Next.js from the Luxride static mirror

**Date:** 13 August 2026
**Source:** `~/Desktop/luxride-nextjs.vercel.appx` (scraped static mirror)
**Target:** Next.js 15 App Router, consuming the Django API already built

---

## 1. What we are actually working from

The provided directory is a **scraped mirror of a deployed demo**, not a project.

| | |
|---|---|
| `.jsx` / `.tsx` source files | **0** |
| Minified JS chunks | 58 |
| Sourcemaps | **0** — no source recovery possible |
| Rendered HTML pages | 70 |
| Compiled CSS | 418 KB (2 files) |
| Images | 187 files, 9.4 MB |

So the original React components do not exist and cannot be recovered. What *is*
usable is better than it sounds:

- **The rendered HTML is clean semantic markup** with meaningful class names —
  roughly 57% of each file is real markup, the rest is React Server Component
  payload inside `<script>` tags, which we strip.
- **The CSS was compiled for exactly that markup**, so it works unchanged.
- The images are usable for a validation build.

**Approach: convert the rendered HTML into React components, keep the CSS
verbatim.** The design is preserved exactly; what gets written is the component
layer and the data wiring.

### Licensing position, recorded once

This is a commercial template ("Lixride Chauffeur Limousine … Nextjs Template")
and the mirror is of its public demo. The client has stated this build is for
**validation and testing only**, with assets to be replaced before production.
That decision is recorded here and not revisited. Before any public launch the
template must be licensed or the design replaced, and the stock photography
swapped for the client's own vehicles — which is an improvement regardless: a
limo company's site should show its actual cars.

---

## 2. What converts cleanly, and what does not

**Converts mechanically** — HTML to JSX, ~10 pages:
markup, class names, layout, typography, spacing, the entire visual design.

**Must be reimplemented** — these were React components; only their *output* was
captured:

| Template dependency | Evidence | Replacement |
|---|---|---|
| Swiper (carousels) | CSS + markup | `swiper/react` — same DOM and class names, so the CSS still applies |
| Slick (carousel) | CSS only | Do not add jQuery. Use Swiper and override the few `.slick-*` rules |
| Datepicker | CSS | `react-day-picker`, restyled — the booking form needs a date and time |
| Select2 (styled selects) | CSS | Native `<select>` styled to match, or headless component |
| Accordion (6 on the homepage) | markup | ~20 lines of React state |
| Mobile burger menu | markup | ~20 lines of React state |
| Sticky header | markup class | scroll listener |

The jQuery-era libraries are the main trap. Their CSS assumes a DOM those
plugins generate at runtime; a React replacement must either reproduce that DOM
or override the rules. Swiper is a straight swap; the other two need a little
CSS work.

---

## 3. Page mapping

Ten pages from seventy. Everything else in the mirror is variants (home-2 …
home-10) and pages this business does not have.

| Template page | Our route | Data source |
|---|---|---|
| `index.html` | `/` | `GET /api/pages/wwwaustinlimoshuttlecom/`, `GET /api/vehicles/` |
| `about.html` | `/about-us` | `GET /api/pages/about-us/` |
| `fleet-list.html` | `/fleet` | `GET /api/vehicles/` |
| `service-single/1–4` | the four SEO service slugs | `GET /api/pages/<slug>/` |
| `contact.html` | `/contact-us` | `POST /api/enquiries/` |
| `booking-vehicle.html` | `/book/vehicle` | `POST /api/quotes/` |
| `booking-passenger.html` | `/book/account` | `POST /api/auth/login/` or guest |
| `booking-payment.html` | `/book/payment` | `POST /api/bookings/`, `POST /api/payments/intent/` |
| `booking-receved.html` | `/book/confirmation/[reference]` | `GET /api/account/bookings/<ref>/` |
| `login.html` / `register.html` | `/account/sign-in`, `/account/register` | `POST /api/auth/*` |

**The template's booking flow maps almost exactly onto ours** — vehicle →
passenger → payment → received. That is the single luckiest thing about this
template and saves the most work.

### URLs that must not change

Nine paths carry the business's search rankings and must be byte-identical:

```
/austin-airport-car-service      /wedding-limousine-services
/executive-transportation-service /graduations-parties-limousine
/fleet   /contact-us   /about-us   /privacy-policy   /terms-conditions
```

The two malformed legacy slugs (`wwwaustinlimoshuttlecom`,
`httpswwwaustinlimoshuttlecom`) map to `/` and the services page, with 301s from
the old forms.

---

## 4. Architecture

```
frontend/
├── app/
│   ├── (marketing)/          # SSR/ISR — SEO-critical
│   │   ├── page.tsx                    /
│   │   ├── [slug]/page.tsx             CMS pages incl. the 4 service pages
│   │   ├── fleet/page.tsx
│   │   └── contact-us/page.tsx
│   ├── book/                 # client components — the funnel
│   │   ├── details/ vehicle/ account/ payment/
│   │   └── confirmation/[reference]/
│   ├── account/              # sign-in, bookings
│   ├── sitemap.ts robots.ts
│   └── layout.tsx
├── components/
│   ├── layout/    Header, Footer, MobileMenu
│   ├── ui/        Accordion, Carousel, DatePicker, Select
│   └── booking/   QuoteForm, VehicleCard, FareBreakdown, StripePayment
├── lib/
│   ├── api.ts           typed client generated from docs/openapi.yaml
│   └── types.ts
└── public/
    ├── assets/imgs/     187 images, lifted from the mirror
    └── styles/luxride.css   418 KB, verbatim
```

**Hosting:** Vercel for the frontend, Django stays on InMotion — recommended and
not yet decided. If the client insists on one host, it becomes a second cPanel
Node app; workable, more friction, and Next must be built in CI rather than on
the server.

**Auth:** both apps under one parent domain so the Django session cookie is
shared (`www.` and `api.` with `SESSION_COOKIE_DOMAIN=.austinlimoshuttle.com`).
Cross-origin means CORS plus CSRF plumbing on every write — decide before
writing the API client, it is unpleasant to retrofit.

---

## 5. Phases

Each phase ends with a green check and a short written QA note, as with the
backend.

### Phase F0 — Scaffold and asset lift
Next.js 15 + TypeScript project. Copy the 187 images and 418 KB of CSS in
verbatim. Generate the typed API client from `docs/openapi.yaml`. Verify the
fonts the CSS expects — none are bundled in the mirror, so they are either
Google-hosted or system; self-host whichever it is.
**Exit:** a blank page renders with the template's typography and colours.

### Phase F1 — Layout shell
Header, footer, mobile menu, sticky-header behaviour — the parts every page
shares. This is where most of the reimplemented interactivity lands.
**Exit:** shell matches the demo at desktop, tablet and mobile widths.

### Phase F2 — Marketing pages + SEO cutover ⭐
The four service pages, home, about, fleet, contact. Content from the API,
`generateMetadata` from our stored meta fields, `sitemap.ts`, `robots.ts`,
`LocalBusiness` and `Service` structured data (the legacy site has none).
**Exit:** all nine protected URLs resolve byte-identically; meta tags match what
Django holds; Lighthouse SEO ≥ 95.
**Highest-risk phase** — this is where rankings are won or lost.

### Phase F3 — Quote and vehicle selection
The booking form: addresses, date, time, passengers. Calls `POST /api/quotes/`,
renders a card per vehicle with the fare breakdown.
**Exit:** a real quote from the live engine renders; the response carries no
distance or price the client supplied.

### Phase F4 — Account step and guest checkout
Sign in, register, or continue as a guest.
**Exit:** all three routes reach the payment step with a valid quote token.

### Phase F5 — Payment
Stripe Elements against `POST /api/payments/intent/`. **Confirmation is by
webhook, not by the browser** — the page shows a pending state and polls
`/api/account/bookings/<ref>/`.
**Exit:** an end-to-end booking in Stripe test mode, confirmed by webhook, with
the confirmation email received.

### Phase F6 — Customer account
Booking list, booking detail, cancellation, password reset entry point.
**Exit:** a migrated legacy customer can reset a password, sign in and see their
historical bookings.

### Phase F7 — Polish and handover
404, loading and error states, accessibility pass, image optimisation, README.
**Exit:** clean Lighthouse run; the client can click through the whole thing.

---

## 6. Data wiring notes

**The API contract is already fixed and documented** — 17 endpoints in
`docs/openapi.yaml`. Two rules the frontend must respect:

1. **Never send a price or a distance.** Post two addresses to `/api/quotes/`,
   receive a signed `quote_token`, present that token when booking. The server
   re-measures and recomputes.
2. **Never treat a browser-side card confirmation as payment.** Stripe's webhook
   confirms the booking. Show pending and poll.

Everything the pages display — vehicles, rates, page copy, meta tags, blackout
dates — comes from the API. No content is hardcoded in the frontend.

---

## 7. Risks

| Risk | Mitigation |
|---|---|
| **jQuery-plugin CSS without the plugins** | Swiper is a straight swap; datepicker and select need CSS overrides. Budget time in F1, not F3. |
| **SEO regression at cutover** | F2 exit criteria check every protected URL byte-for-byte before anything ships. |
| **RSC payload noise in the scraped HTML** | Strip `<script>` blocks during conversion; they are build artefacts, not content. |
| **Template CSS specificity fights** | Keep `luxride.css` untouched and add overrides in a separate file, so the template can be swapped wholesale later. |
| **Images are stock and unlicensed** | Validation build only, per the client. Replace before launch — tracked in `outstanding-notes.html`. |
| **Hosting undecided** | Blocks nothing until F7, but decide before the deployment phase. |

---

## 8. Decisions needed

1. **Vercel or InMotion for the frontend?** Recommended: Vercel. Changes the
   build and deploy story, nothing else.
2. **Same parent domain for both apps?** Strongly recommended — it makes auth
   simple. Decide before F3.
3. **Which of the ten homepage variants** does the client want? The mirror has
   `index` plus `home-2` … `home-10`. Picking one now avoids rework in F2.

---

## 9. What this plan deliberately excludes

- **Puck.** Discussed and deferred: build the pages first, see which patterns
  repeat, then turn those into editor blocks. Puck comes after launch, and needs
  the content write-endpoints and media library that do not exist yet.
- **Blog.** Dropped per the client. `/blog/*` still needs 301s before WordPress
  is removed.
- **Any change to the Django backend.** The API is complete for everything above.
  If a gap appears, it is a finding worth surfacing rather than patching around.

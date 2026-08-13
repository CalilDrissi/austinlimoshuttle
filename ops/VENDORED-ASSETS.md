# Vendored front-end assets

Bootstrap and its icon font are **downloaded into the repository** and served
from our own domain. They are not linked from a CDN, and must not be.

| Asset | Version | Path |
|---|---|---|
| Bootstrap CSS | 5.3.3 | `backend/static/vendor/bootstrap/bootstrap.min.css` |
| Bootstrap JS bundle | 5.3.3 | `backend/static/vendor/bootstrap/bootstrap.bundle.min.js` |
| Bootstrap Icons CSS | 1.11.3 | `backend/static/vendor/bootstrap/bootstrap-icons.min.css` |
| Bootstrap Icons fonts | 1.11.3 | `backend/static/vendor/bootstrap/fonts/` |
| Source maps | 5.3.3 | `bootstrap.min.css.map`, `bootstrap.bundle.min.js.map` |

**The source maps are not optional.** Production uses
`ManifestStaticFilesStorage`, which parses CSS and JS for referenced files.
Bootstrap's minified files end with a `sourceMappingURL` comment, so a missing
`.map` makes `collectstatic` fail outright with
`ValueError: The file ... could not be found` — the deploy stops, rather than
merely losing devtools support.

## Why local rather than a CDN

`config/middleware.py` sets a Content-Security-Policy with `script-src 'self'`
and `font-src 'self'`. A `<script src="https://cdn.jsdelivr.net/...">` would be
**blocked by the browser**, and the page would render as unstyled HTML with no
error visible on the server. Local assets are same-origin and satisfy the policy.

Three other reasons the local copy is the right call here:

- **The site works without third-party availability.** A CDN outage cannot take
  the dispatch board down mid-shift.
- **No third party learns who uses the admin.** A CDN request leaks the
  referring URL and the staff member's IP on every page load.
- **Nothing changes underneath us.** A vendored file is the file that was
  reviewed and tested.

## Updating

```bash
cd backend
BS=5.3.3
ICONS=1.11.3
BASE=https://cdn.jsdelivr.net/npm

curl -sSL "$BASE/bootstrap@$BS/dist/css/bootstrap.min.css" \
     -o static/vendor/bootstrap/bootstrap.min.css
curl -sSL "$BASE/bootstrap@$BS/dist/js/bootstrap.bundle.min.js" \
     -o static/vendor/bootstrap/bootstrap.bundle.min.js
curl -sSL "$BASE/bootstrap-icons@$ICONS/font/bootstrap-icons.min.css" \
     -o static/vendor/bootstrap/bootstrap-icons.min.css
curl -sSL "$BASE/bootstrap-icons@$ICONS/font/fonts/bootstrap-icons.woff2" \
     -o static/vendor/bootstrap/fonts/bootstrap-icons.woff2
curl -sSL "$BASE/bootstrap-icons@$ICONS/font/fonts/bootstrap-icons.woff" \
     -o static/vendor/bootstrap/fonts/bootstrap-icons.woff

# Source maps -- required, see above
curl -sSL "$BASE/bootstrap@$BS/dist/css/bootstrap.min.css.map" \
     -o static/vendor/bootstrap/bootstrap.min.css.map
curl -sSL "$BASE/bootstrap@$BS/dist/js/bootstrap.bundle.min.js.map" \
     -o static/vendor/bootstrap/bootstrap.bundle.min.js.map
```

The CDN is used **only to fetch the files during an upgrade**. The running
application never contacts it.

Afterwards, update the versions in the table above, then **run
`manage.py collectstatic --settings=config.settings.prod`** — that is what
catches a missing source map, and it is the check the development server will
not perform for you. Also confirm the icon CSS still resolves its fonts
relatively (`url("fonts/bootstrap-icons.woff2")`) — that relative path is why
the fonts live in a `fonts/` subdirectory beside the CSS.

## Deployment

`collectstatic` copies these into `STATIC_ROOT`
(`/home/austi118/public_html/static` in production). Production uses
`ManifestStaticFilesStorage`, so the served filenames are content-hashed and can
be cached indefinitely.

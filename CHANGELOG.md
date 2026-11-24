# Changelog

All notable changes to scrapalyser are listed here.
The format follows [Keep a Changelog](https://keepachangelog.com/) and versions follow [Semantic Versioning](https://semver.org/).

## [0.2.0] — 2026-11-24

Tested on about 30 real sites protected by Cloudflare, Turnstile, Akamai, DataDome, PerimeterX,
Kasada, Imperva, Sucuri, Fastly, AWS WAF, reCAPTCHA and hCaptcha, with and without a proxy.

### Added
- **Automatic engine fallback** (`engine="auto"`, the new default): curl_cffi first, Playwright if
  curl_cffi is blocked. The first engine that gets through produces the report; the `attempts`
  field and the `[ENGINES]` section show what each engine got and which one to use.
- **Blocking diagnosis** (`blocking` field, `[BLOCKING]` section): why you are blocked — IP banned,
  country blocked, browser signature, firewall rule, rate limit, JS challenge, captcha — with the
  Cloudflare error code, Ray ID and what to try next.
- **Proxy support** (`proxy=`) for both engines. Accepted formats: `http://USER:PASSWORD@HOST:PORT`,
  `USER:PASSWORD@HOST:PORT`, `HOST:PORT:USER:PASSWORD`, `USER:PASSWORD:HOST:PORT`, `HOST:PORT`.
  Credentials never appear in the report or in error messages.
- **Several sites in one call**: `scan([url1, url2, ...], workers=4)` scans a list of sites in
  parallel (`workers` = how many at the same time); results in the same order as the list; a
  failing site does not stop the others; optional `save_dir`. `scan_many()` does the same.
- **Embedded data detection** (`embedded_data`): JSON already in the HTML — `__NEXT_DATA__`, Nuxt,
  JSON-LD / schema.org types, `window.__INITIAL_STATE__`, Apollo, Remix, Next.js App Router.
- **robots.txt rules**: whether the scanned page is allowed, and the `Crawl-delay`.
- **Every sitemap** declared in robots.txt (`sitemap.urls`), each one checked to really answer.
- **Rate limit headers** (`rate_limit`): `Retry-After`, `X-RateLimit-*`, `RateLimit-*`.
- **`timeout` parameter** (default 30 s) for slow sites and proxies.
- **Command line**: `scrapalyser https://example.com` (also `python -m scrapalyser`), proxy from
  `--proxy` or the `SCRAPALYSER_PROXY` environment variable.
- **Antibots**: Fastly and AWS WAF / CloudFront; `antibot.all` lists every protection found.
- **Test suite** (pytest, offline): `pip install -e ".[dev]"` then `pytest`.

### Changed
- ⚠️ Default engine is now `"auto"` (was `"curl"`). Pass `engine="curl"` for the old behaviour.
- ⚠️ Playwright now runs with a **visible browser** by default (`headless=False`): headless Chromium
  is much easier for antibots to spot. Pass `headless=True` on a server without a screen.
- ⚠️ Playwright is now a **required** dependency (run `playwright install chromium` once).
  `pip install scrapalyser[playwright]` still works.
- ⚠️ `login_wall.detected` now means a **required** login; the new `login_wall.login_available`
  flags an optional one (login button, OAuth).
- Playwright keeps the real browser's user agent (no fake Windows / Chrome 124 one) and hides
  `navigator.webdriver`.
- `js_required` is measured on the raw HTML sent by the server, with both engines: server-rendered
  Next.js / Nuxt pages are no longer reported as needing JavaScript.
- The text report is printed once, in English by default, with `"blocked by antibot"` translated.

### Fixed
- Sitemap URL from robots.txt now returned instead of a default `/sitemap.xml`.
- Cloudflare Turnstile reported on every Cloudflare site: now only when its script is present.
- Antibot cookies matched by prefix (Imperva `incap_ses_<id>`, `nlbi_<id>`…).
- False "blocked by antibot": generic phrases such as "access denied" only count in the title or on
  an almost empty page; 401 and 503 alone no longer count; Cloudflare `cf-mitigated` is used.
- Block pages served with **status 200** (Akamai "Reference #…") are now detected.
- Kasada not detected (real headers / cookies / `ips.js` now used); its 429 is a JS challenge, not a
  rate limit.
- Akamai and reCAPTCHA signatures completed (`akamai-grn`, `_abck`, relative `/recaptcha/api.js`).
- Google results detected as WordPress (links to WordPress sites): only the site's own files count.
- Playwright read third-party cookies (ads, widgets) and reported their antibot as the site's.
- Playwright reloaded the whole page after a `networkidle` timeout (twice the wait, frequent timeouts
  behind a proxy).
- Playwright crashed when a solved challenge page reloaded itself; it now waits for the new page.
- A page Playwright could not load at all (status 0) was counted as a success.
- JS detection now counts only visible text (inline JSON / CSS excluded); `<div id="root" class="…">`
  recognised.
- `/author` mistaken for a login page (`/auth`).
- `__version__` aligned with the package version.

## [0.1.2] and earlier

- Comments translated to English; Imperva, Sucuri and custom antibot detection.
- First releases: antibot, technology, JS, API, robots.txt, sitemap and login wall detection.

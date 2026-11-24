# scrapalyser

[![PyPI version](https://badge.fury.io/py/scrapalyser.svg)](https://pypi.org/project/scrapalyser/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Pre-scraping intelligence tool. Scan any website before writing a single line of scraper.

---

## Install

```bash
pip install scrapalyser
playwright install chromium
```

---

## Usage

```python
import scrapalyser

# Simple scan — returns a dict
report = scrapalyser.scan("https://example.com")
print(report)

# Full options
report = scrapalyser.scan(
    url="https://example.com",
    output="txt",           # "json" (default) or "txt"
    lang="en",              # "en" (default), "fr", "es", "br"
    save="report.txt",      # optional — write output to file
    engine="auto",          # "auto" (default), "curl" or "playwright"
    headless=False,         # False (default, visible browser, harder to detect) or True — playwright only
    screenshot="shot.png",  # optional — playwright only
    proxy="http://user:pass@host:port",  # optional — used by both engines
)
```

## Using a proxy

Pass your proxy with the `proxy` parameter. Write it in this format:

```
http://USER:PASSWORD@HOST:PORT
```

| Part | What to put | Example |
|---|---|---|
| `http://` | The proxy type. Keep `http://` unless your provider says otherwise | `http://` |
| `USER` | The username your provider gave you | `alice` |
| `PASSWORD` | The password your provider gave you | `s3cret` |
| `HOST` | The proxy address | `gw.provider.com` |
| `PORT` | The proxy port | `823` |

```python
import scrapalyser

report = scrapalyser.scan(
    "https://example.com",
    proxy="http://alice:s3cret@gw.provider.com:823",
)
```

Follow this format and scrapalyser will use your proxy with **both engines**: curl_cffi and
Playwright, plus the robots.txt and sitemap requests. You write it once, scrapalyser converts it
for each engine.

Tip: keep the proxy out of your code. Put it in a `.env` file (and add `.env` to `.gitignore`):

```
PROXY="http://alice:s3cret@gw.provider.com:823"
```

```python
import os
report = scrapalyser.scan("https://example.com", proxy=os.environ["PROXY"])
```

### Other accepted formats

Providers do not all give the proxy in the same shape. These are accepted too:

| Format | Example |
|---|---|
| `USER:PASSWORD@HOST:PORT` | `alice:s3cret@gw.provider.com:823` |
| `HOST:PORT:USER:PASSWORD` | `gw.provider.com:823:alice:s3cret` |
| `USER:PASSWORD:HOST:PORT` | `alice:s3cret:gw.provider.com:823` |
| `HOST:PORT` (proxy without password) | `1.2.3.4:8080` |

### Good to know

- **Proxy types:** `http://` (default), `https://`, `socks5://`, `socks5h://`, `socks4://`.
- **SOCKS5 with a password does not work with Playwright** (Chromium limit). Use `http://` if you want both engines.
- **Special characters** in the password (`@`, `:`) are fine.
- **Wrong format:** scrapalyser raises a `ValueError` listing the accepted formats.
- **Wrong password:** the error says the proxy refused the credentials (HTTP 407).
- **Privacy:** the report shows only `HOST:PORT`, never your username or password.

---

## Example output

### JSON

```json
{
  "url": "https://example.com",
  "scanned_at": "2026-05-19T12:32:00Z",
  "status_code": 200,
  "engine": "curl",
  "proxy": null,
  "attempts": [
    {"engine": "curl", "status_code": 200, "passed": true, "blocking": null}
  ],
  "antibot": {
    "detected": true,
    "name": "Cloudflare Turnstile"
  },
  "technology": {
    "type": "React"
  },
  "js_required": true,
  "api": {
    "detected": true,
    "endpoints": [
      "https://api.example.com/v1/search"
    ]
  },
  "robots_txt": {
    "found": true,
    "url": "https://example.com/robots.txt"
  },
  "sitemap": {
    "found": true,
    "url": "https://example.com/sitemap.xml"
  },
  "login_wall": {
    "detected": false,
    "type": null,
    "login_available": true
  },
  "blocking": null
}
```

### TXT

```
═══════════════════════════════════════════
        SCRAPALYSER REPORT
        https://example.com
        Scanned at : 2026-05-19T12:32:00Z
        Status : 200
═══════════════════════════════════════════

[ENGINES]
  ✅  curl_cffi : passes (200)
  👉  Engine to use for this site : curl_cffi

[ANTI-BOT]
  ⚠️  Detected : Cloudflare Turnstile

[TECHNOLOGY]
  🖥️  Type : React

[JAVASCRIPT]
  ⚠️  JS required: Yes → use Playwright

[DETECTED APIs]
  ✅  https://api.example.com/v1/search

[ROBOTS.TXT]
  ✅  https://example.com/robots.txt

[SITEMAP]
  ✅  https://example.com/sitemap.xml

[LOGIN WALL]
  ✅  No login required (optional login available)

═══════════════════════════════════════════
```

The text report is in English by default. Set `lang="fr"`, `"es"` or `"br"` for French, Spanish or Brazilian Portuguese.

---

## Features

- 🛡️ **Anti-bot detection** — Cloudflare, DataDome, PerimeterX, Akamai, Kasada, Imperva, Sucuri, reCAPTCHA, hCaptcha + Unknown/Custom antibot detection
- 🖥️ **Technology detection** — React, Vue, Angular, Next.js, Nuxt, Svelte, WordPress, Shopify, Drupal, Joomla, Wix, Webflow
- ⚡ **JS requirement detection** — know before you write whether curl_cffi is enough or Playwright is needed
- 🌐 **API endpoint discovery** — via CSP headers, inline scripts, and XHR/Fetch interception (Playwright mode)
- 🤖 **robots.txt parser** — URL extraction with common path variants (`/robot.txt`, `/robots.txt`)
- 🗺️ **Sitemap detection** — via robots.txt or direct probe (`/sitemap.xml`, `/sitemaps.xml`...)
- 🔐 **Login wall detection** — tells a *required* login (redirect, HTTP 401, login-only page) apart from an *optional* one (login button, OAuth)
- 🔀 **Proxy support** — one `proxy="http://USER:PASSWORD@HOST:PORT"` works with both engines (see [Using a proxy](#using-a-proxy))
- 📸 **Screenshot** — capture the page as seen by the browser (Playwright mode)
- 🔁 **Automatic engine fallback** — curl_cffi first, Playwright if blocked; the report tells you which engine to use
- 🚫 **Blocked by antibot** — if both engines are blocked, the other fields return `"blocked by antibot"`
- ⛔ **Blocking diagnosis** — tells *why* you are blocked (IP banned, country blocked, browser signature, firewall rule, rate limit, JS challenge, captcha) with the Cloudflare error code, Ray ID and what to try next
- 🌍 **Multi-language output** — fr, en, es, br
- 📄 **JSON & TXT export** — machine-readable or human-readable

---

## Engines

By default (`engine="auto"`), scrapalyser tries **curl_cffi** first (fast, browser-like TLS
fingerprint, no need for `requests`). If curl_cffi is blocked by an antibot, it retries with
**Playwright** (real Chromium). The first engine that gets through produces the report, and the
`attempts` field shows what each engine got, so you know which one to use for your scraper.
The blocked report (with its `blocking` diagnosis) is only returned when **both** engines are blocked.

Force a single engine with `engine="curl"` or `engine="playwright"`.

| Feature | `curl` | `playwright` |
|---|---|---|
| Speed | ⚡ Fast | 🐢 Slower |
| JS execution | ❌ | ✅ |
| XHR/Fetch API detection | ❌ | ✅ |
| Screenshot | ❌ | ✅ |
| Bot bypass | Partial | Better (visible browser by default, `headless=False`) |

Playwright runs with the real browser's user agent (no fake one that would contradict the rest of
the fingerprint) and `navigator.webdriver` hidden. Keep the default `headless=False` when you can:
headless Chromium is easier to spot (no plugins, software-rendered WebGL), so some sites send no data to it.

---

## Anti-bot detection

When the site blocks you (403, 429, captcha/challenge page) — with both engines in `auto` mode —
scrapalyser reports which antibot is responsible, **why** you are blocked, and marks the other
fields as `"blocked by antibot"`, so you know exactly what you're up against before writing anything.

The `blocking` field (`null` when not blocked) explains the block:

```json
"blocking": {
  "reason": "ip_banned",
  "code": "1006",
  "ray_id": "a5f6f386fedaef9a-MRS"
}
```

| `reason` | Meaning | What to try |
|---|---|---|
| `ip_banned` | Cloudflare 1005–1008 | Another IP (residential proxy): changing browser won't help |
| `country_blocked` | Cloudflare 1009 | An IP in the site's country |
| `browser_signature` | Cloudflare 1010 | Real browser / another TLS fingerprint |
| `firewall_rule` | Cloudflare 1012, 1020 | Real browser, then another IP |
| `rate_limited` | HTTP 429, Cloudflare 1015 | Slow down, rotate IPs |
| `js_challenge` | Challenge page (`cf-mitigated`, "Just a moment…") | Real browser (Playwright) |
| `captcha` | Turnstile, DataDome, PerimeterX, reCAPTCHA, hCaptcha | Real browser + captcha solver |
| `access_denied` | Blocked, no specific reason found | Real browser, then another IP |

Supported:
| Solution | Detection method |
|---|---|
| Cloudflare | `cf-ray` header, `__cf_bm` cookie |
| Cloudflare Turnstile | `challenges.cloudflare.com/turnstile` script |
| DataDome | `x-datadome` header, `datadome` cookie |
| PerimeterX | `_px` cookie, script patterns |
| Akamai | `ak_bmsc` / `bm_sz` cookies |
| Kasada | `kkrta` / `kasada.io` scripts |
| Imperva | `x-iinfo` header, `incap_ses` cookie |
| Sucuri | `x-sucuri-id` header |
| reCAPTCHA | script pattern |
| hCaptcha | script pattern |
| Unknown / Custom | suspicious headers, cookies, obfuscated scripts |

---

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Commit your changes
4. Open a pull request

---

## License

MIT — see [LICENSE](LICENSE).

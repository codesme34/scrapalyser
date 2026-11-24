# scrapalyser

[![PyPI version](https://badge.fury.io/py/scrapalyser.svg)](https://pypi.org/project/scrapalyser/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Scan a website before you write your scraper.**
> scrapalyser tells you what protects the site, whether you will get blocked, which tool to use,
> and where the data is.

One scan answers the questions you would otherwise find out the hard way:

- 🛡️ **Is there an antibot?** Cloudflare, DataDome, Akamai, PerimeterX, Kasada… and if it blocks you, **why**.
- 🔁 **Which tool should I use?** curl_cffi is tried first, then a real browser (Playwright) if it gets blocked.
- ⚡ **Do I need JavaScript?** Or is the page complete without it.
- 📦 **Where is the data?** JSON already in the HTML (`__NEXT_DATA__`, JSON-LD…), API endpoints, sitemaps.
- 🤖 **What are the rules?** robots.txt, crawl delay, rate limits, login wall.

---

## Contents

1. [Install](#install)
2. [Quick start](#quick-start)
3. [Reading the report](#reading-the-report)
4. [Options](#options)
5. [Scanning several sites](#scanning-several-sites)
6. [Using a proxy](#using-a-proxy)
7. [Your IP affects the report](#your-ip-affects-the-report)
8. [How it works](#how-it-works)
9. [JSON reference](#json-reference)
10. [Contributing](#contributing)

---

## Install

```bash
pip install scrapalyser
playwright install chromium     # once: downloads the browser used when curl_cffi is blocked
```

Python 3.9 or newer.

---

## Quick start

### In Python

```python
import scrapalyser

report = scrapalyser.scan("https://example.com")                # returns a dict (JSON)
scrapalyser.scan("https://example.com", output="txt")           # prints a readable report

# Several sites at once: give a list, choose how many run at the same time
reports = scrapalyser.scan(["https://site1.com", "https://site2.com"], workers=4)
```

### In a terminal

```bash
scrapalyser https://example.com                  # readable report
scrapalyser https://example.com --json           # JSON
scrapalyser https://example.com --lang fr        # report in French (en, fr, es, br)
scrapalyser --help                               # every option
```

`python -m scrapalyser ...` works too.

---

## Reading the report

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
  ⚠️  Detected : Cloudflare, reCAPTCHA

[TECHNOLOGY]
  🖥️  Type : Next.js

[JAVASCRIPT]
  ✅  JS required: No → curl_cffi is enough

[DETECTED APIs]
  ✅  https://api.example.com/v1/search

[EMBEDDED DATA]
  💡  Data readable directly, no page parsing needed
  ✅  JSON-LD (schema.org) → script[type="application/ld+json"] (~21 KB) : ItemList, BreadcrumbList
  ✅  Next.js (__NEXT_DATA__) → script#__NEXT_DATA__ (~930 KB)

[ROBOTS.TXT]
  ✅  https://example.com/robots.txt
  ✅  Scanned page allowed for bots
  ⏱️  Crawl-delay: 5 s between requests

[SITEMAP]
  ✅  https://example.com/sitemap-products.xml
  ✅  https://example.com/sitemap-pages.xml

[RATE LIMIT]
  ⏱️  Limit : 100
  ⏱️  Remaining : 99
  ⏱️  Reset : 60

[LOGIN WALL]
  ✅  No login required (optional login available)

═══════════════════════════════════════════
```

| Section | What it tells you |
|---|---|
| **Engines** | Which engine got through, and the one to use in your scraper |
| **Anti-bot** | Every protection found on the site |
| **Blocking** | Only when every engine is blocked: why, and what to try (see [Blocking reasons](#blocking-reasons)) |
| **Technology** | The framework or CMS (Next.js, Nuxt, React, WordPress, Shopify…) |
| **JavaScript** | Whether the page is complete without running JS |
| **Detected APIs** | API endpoints the page calls: often easier to use than the HTML |
| **Embedded data** | JSON already inside the HTML, and where to find it: read it instead of parsing the page |
| **robots.txt** | Its URL, whether the scanned page is allowed, the delay asked between requests |
| **Sitemap** | Every working sitemap: the list of the site's pages |
| **Rate limit** | How many requests you get and how long to wait, when the server says so |
| **Login wall** | Whether a login is **required**, or only available |

When a site blocks every engine, the sections that need the page show `blocked by antibot`.

---

## Options

```python
report = scrapalyser.scan(
    url="https://example.com",  # one URL, or a list of URLs
    output="json",          # "json" (default) or "txt"
    lang="en",              # text report language: "en" (default), "fr", "es", "br"
    save="report.txt",      # optional: write the report to a file
    engine="auto",          # "auto" (default), "curl" or "playwright"
    headless=False,         # Playwright: False (default) = visible browser, harder to detect
    screenshot="shot.png",  # optional: Playwright screenshot
    proxy="http://USER:PASSWORD@HOST:PORT",  # optional: see "Using a proxy"
    timeout=30,             # seconds to wait for the page (default 30)
    workers=4,              # with a list of URLs: how many sites are scanned at the same time (default 4)
    save_dir="reports",     # optional: a folder, one report file per site
)
```

| Option | Default | When to change it |
|---|---|---|
| `engine` | `"auto"` | Force `"curl"` or `"playwright"` to test one engine only |
| `headless` | `False` | `True` on a server without a screen (but headless is easier for antibots to spot) |
| `timeout` | `30` | Raise it for slow sites or slow proxies |
| `workers` | `4` | With a list of URLs: how many sites are scanned at the same time (see [Scanning several sites](#scanning-several-sites)) |
| `save_dir` | — | A folder to write the reports, one file per site |

Same options on the command line: `--engine`, `--headless`, `--timeout`, `--proxy`, `--save`,
`--screenshot`, `--lang`, `--json`, and for several URLs `--workers` and `--save-dir`.

---

## Scanning several sites

Give `scan()` a **list of URLs**. `workers` sets how many sites are scanned at the same time:

```python
reports = scrapalyser.scan(
    ["https://site1.com", "https://site2.com", "https://site3.com"],
    workers=4,              # 1 = one after the other, 4 (default), 10...
    save_dir="reports",     # optional: one file per site (001_site1.com.json, ...)
)
```

```bash
scrapalyser https://site1.com https://site2.com https://site3.com --workers 4 --save-dir reports
```

- You get **a list of reports, in the same order as your URLs**.
- A site that fails does not stop the others: its result is `{"url": ..., "error": ...}`.
- All the other options work the same way (`proxy`, `engine`, `timeout`…). `save` and
  `screenshot` take one URL: use `save_dir` with a list.
- Each Playwright scan opens its own browser (~200–300 MB of RAM): 10 workers can mean 10 Chrome windows.
- Use workers to scan **different sites**. Many parallel scans of the same site is the fastest way to get blocked.

`scrapalyser.scan_many(urls, workers=4)` does the same thing, if you prefer a separate function.

---

## Using a proxy

Write your proxy in this format:

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
report = scrapalyser.scan("https://example.com", proxy="http://alice:s3cret@gw.provider.com:823")
```

Written this way, the proxy is used by **both engines** (curl_cffi and Playwright) and by the
robots.txt and sitemap checks. You write it once, scrapalyser converts it for each engine.

**Keep the proxy out of your code.** Put it in an environment variable or a `.env` file (and add
`.env` to `.gitignore`):

```python
import os
report = scrapalyser.scan("https://example.com", proxy=os.environ["PROXY"])
```

```bash
export SCRAPALYSER_PROXY="http://USER:PASSWORD@HOST:PORT"   # read by the command line
scrapalyser https://example.com
```

<details>
<summary><b>Other accepted formats and details</b></summary>

Providers do not all give the proxy in the same shape. These are accepted too:

| Format | Example |
|---|---|
| `USER:PASSWORD@HOST:PORT` | `alice:s3cret@gw.provider.com:823` |
| `HOST:PORT:USER:PASSWORD` | `gw.provider.com:823:alice:s3cret` |
| `USER:PASSWORD:HOST:PORT` | `alice:s3cret:gw.provider.com:823` |
| `HOST:PORT` (no password) | `1.2.3.4:8080` |

- **Proxy types:** `http://` (default), `https://`, `socks5://`, `socks5h://`, `socks4://`.
- **SOCKS5 with a password does not work with Playwright** (Chromium limit): use `http://` for both engines.
- **Special characters** in the password (`@`, `:`) are fine.
- **Wrong format:** a `ValueError` lists the accepted formats.
- **Wrong password:** the error says the proxy refused the credentials (HTTP 407).
- **Privacy:** the report shows only the proxy server (`http://HOST:PORT`), never your username or password.

</details>

---

## Your IP affects the report

⚠️ **The report describes what the site does for the IP that scanned it** — your own IP or a
proxy's. Antibots judge the IP, not only the request:

- **Your own IP** may already be flagged: you scraped this site before, you were rate limited,
  your network is shared (office, school, VPN, mobile carrier), or it belongs to a datacenter
  (servers, cloud, CI). The site may block you and let other people through.
- **A proxy IP** may be banned or flagged too. With a rotating proxy, each scan uses a different
  IP: one can be blocked and the next one pass.
- **The country** of the IP matters: some sites block, challenge or redirect foreign visitors.

So "blocked" does not always mean the site blocks everyone, and "passed" does not guarantee your
scraper will always get through. The blocking reasons `ip_banned`, `country_blocked` and
`rate_limited` point to the IP, not to your code.

### For an accurate report, run several tests

One scan is one IP at one moment. Before deciding how to build your scraper:

1. Scan a few times **without a proxy** (your own IP).
2. Scan a few times **with a proxy**.
3. **Compare.** Always the same result: you can trust it. Different results: the site judges IPs
   one by one, so plan for a proxy and retries in your scraper.

Leave a little time between scans of the same site: scanning it many times in a row can itself
get your IP flagged.

---

## How it works

### Engines

With `engine="auto"` (the default):

1. **curl_cffi** is tried first: fast, with a real Chrome TLS fingerprint (no need for `requests`).
2. If an antibot blocks it, **Playwright** (a real Chromium browser) tries.
3. The first engine that gets through produces the report. The `attempts` field and the
   `[ENGINES]` section show what each engine got.
4. Only when **both** are blocked does the report explain the block.

| | `curl` | `playwright` |
|---|---|---|
| Speed | ⚡ Fast | 🐢 Slower |
| Runs JavaScript | ❌ | ✅ |
| Sees API calls made by the page (XHR / fetch) | ❌ | ✅ |
| Screenshot | ❌ | ✅ |
| Gets past antibots | Sometimes | More often |

Playwright keeps the real browser's user agent (no fake one that contradicts the rest of the
fingerprint) and hides `navigator.webdriver`. Keep the visible browser (`headless=False`) when you
can: headless Chromium has no plugins and a software graphics card, so some sites send it no data.

### Antibots detected

| Antibot | Detected by |
|---|---|
| Cloudflare | `cf-ray` header, `__cf_bm` cookie |
| Cloudflare Turnstile | `challenges.cloudflare.com/turnstile` script |
| DataDome | `x-datadome` header, `datadome` cookie, captcha script |
| PerimeterX (HUMAN) | `_px*` cookies, `px.js` / `client.perimeterx.net` scripts |
| Akamai | `akamai-grn` header, `_abck` / `ak_bmsc` / `bm_sz` cookies, "Reference #" block pages |
| Kasada | `x-kpsdk-*` headers, `KP_UIDz` / `tkrm_alpekz` cookies, `ips.js` script |
| Imperva | `x-iinfo` header, `incap_ses` / `visid_incap` cookies |
| Sucuri | `x-sucuri-id` header |
| Fastly | `_fs_ch_*` challenge cookies |
| AWS WAF / CloudFront | `x-amz-cf-id` header, `aws-waf-token` cookie |
| reCAPTCHA | `/recaptcha/` script |
| hCaptcha | `hcaptcha.com` script |
| Unknown / Custom | suspicious headers, cookies and obfuscated scripts |

A site often stacks several (a CDN, a bot manager, a captcha): all of them are listed.

### Blocking reasons

When every engine is blocked, the `blocking` field says why:

```json
"blocking": {"reason": "ip_banned", "code": "1006", "ray_id": "a5f6f386fedaef9a-MRS"}
```

| `reason` | Seen as | What to try |
|---|---|---|
| `ip_banned` | Cloudflare 1005–1008 | Another IP (residential proxy): changing browser won't help |
| `country_blocked` | Cloudflare 1009 | An IP in the site's country |
| `browser_signature` | Cloudflare 1010 | A real browser, or another TLS fingerprint |
| `firewall_rule` | Cloudflare 1012 / 1020, AWS WAF | A real browser, then another IP |
| `rate_limited` | HTTP 429, Cloudflare 1015 | Slow down, rotate IPs |
| `js_challenge` | "Just a moment…", Kasada challenge | A real browser (Playwright) |
| `captcha` | Turnstile, DataDome, PerimeterX, reCAPTCHA, hCaptcha | A real browser + a captcha solver |
| `access_denied` | Blocked, no specific reason found | A real browser, then another IP |

---

## JSON reference

`scan()` returns this dict (and `output="json"` / `--json` prints it):

```json
{
  "url": "https://example.com",
  "scanned_at": "2026-05-19T12:32:00Z",
  "status_code": 200,
  "engine": "curl",
  "proxy": null,
  "attempts": [{"engine": "curl", "status_code": 200, "passed": true, "blocking": null}],
  "antibot": {"detected": true, "name": "Cloudflare", "all": ["Cloudflare", "reCAPTCHA"]},
  "blocking": null,
  "rate_limit": {"detected": true, "limit": "100", "remaining": "99", "reset": "60",
                 "retry_after": null, "policy": null, "headers": {"x-ratelimit-limit": "100"}},
  "technology": {"type": "Next.js"},
  "js_required": false,
  "api": {"detected": true, "endpoints": ["https://api.example.com/v1/search"]},
  "embedded_data": {"detected": true, "sources": [
    {"type": "JSON-LD (schema.org)", "selector": "script[type=\"application/ld+json\"]",
     "size": 21960, "schema_types": ["ItemList", "BreadcrumbList"]},
    {"type": "Next.js (__NEXT_DATA__)", "selector": "script#__NEXT_DATA__", "size": 952396}
  ]},
  "robots_txt": {"found": true, "url": "https://example.com/robots.txt", "allowed": true, "crawl_delay": 5.0},
  "sitemap": {"found": true, "url": "https://example.com/sitemap-products.xml",
              "urls": ["https://example.com/sitemap-products.xml", "https://example.com/sitemap-pages.xml"],
              "declared_in_robots": 2},
  "login_wall": {"detected": false, "type": null, "login_available": true}
}
```

| Field | Meaning |
|---|---|
| `engine` | The engine that produced the report (`curl` or `playwright`) |
| `proxy` | The proxy server used (`http://HOST:PORT`), never the credentials; `null` without proxy |
| `attempts` | Every engine tried, in order, and whether it got through |
| `antibot.all` | Every protection found; `antibot.name` is the first one |
| `blocking` | `null` when an engine got through, otherwise the [blocking reason](#blocking-reasons) |
| `rate_limit` | Values read from `Retry-After`, `X-RateLimit-*`, `RateLimit-*` headers |
| `js_required` | `false` when the HTML sent by the server already holds the content |
| `embedded_data.sources` | Each JSON source: `selector` to find it, `size` in bytes, schema.org types for JSON-LD |
| `robots_txt.allowed` | Whether robots.txt allows the scanned page; `crawl_delay` in seconds |
| `sitemap.urls` | Every working sitemap; `sitemap.url` is the first one |
| `login_wall` | `detected` = login **required**; `login_available` = optional login |
| `screenshot` | Playwright only: the screenshot path, if asked |

When every engine is blocked, `technology`, `js_required`, `api`, `embedded_data`, `robots_txt`,
`sitemap` and `login_wall` are `"blocked by antibot"`.

---

## Contributing

1. Fork the repo and create a branch (`git checkout -b feat/my-feature`).
2. Install the dev dependencies and run the tests (offline, no browser needed):
   ```bash
   pip install -e ".[dev]"
   pytest
   ```
3. Commit your changes and open a pull request.

## Changelog

See [CHANGELOG.md](https://github.com/codesme34/scrapalyser/blob/main/CHANGELOG.md).

## License

MIT — see [LICENSE](https://github.com/codesme34/scrapalyser/blob/main/LICENSE).

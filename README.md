# scrapalyser

[![PyPI version](https://badge.fury.io/py/scrapalyser.svg)](https://pypi.org/project/scrapalyser/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Pre-scraping intelligence tool. Scan any website before writing a single line of scraper.

---

## Install

```bash
# Core (curl_cffi engine)
pip install scrapalyser

# With Playwright support
pip install scrapalyser[playwright]
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
    lang="fr",              # "en" (default), "fr", "es", "br"
    save="report.txt",      # optional — write output to file
    engine="curl",          # "curl" (default) or "playwright"
    headless=True,          # True (default) or False — playwright only
    screenshot="shot.png",  # optional — playwright only
)
```

---

## Example output

### JSON

```json
{
  "url": "https://example.com",
  "scanned_at": "2026-05-19T12:32:00Z",
  "status_code": 200,
  "engine": "curl",
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
    "type": null
  }
}
```

### TXT (French)

```
═══════════════════════════════════════════
        SCRAPALYSER RAPPORT
        https://example.com
        Scanné le : 2026-05-19T12:32:00Z
        Status : 200
═══════════════════════════════════════════

[ANTI-BOT]
  ⚠️  Détecté : Cloudflare Turnstile

[TECHNOLOGIE]
  🖥️  Type : React

[JAVASCRIPT]
  ⚠️  JS requis : Oui → utiliser Playwright/Selenium

[API DÉTECTÉES]
  ✅  https://api.example.com/v1/search

[ROBOTS.TXT]
  ✅  https://example.com/robots.txt

[SITEMAP]
  ✅  https://example.com/sitemap.xml

[LOGIN WALL]
  ✅  Aucun login requis

═══════════════════════════════════════════
```

---

## Features

- 🛡️ **Anti-bot detection** — Cloudflare, DataDome, PerimeterX, Akamai, Kasada, Imperva, Sucuri, reCAPTCHA, hCaptcha + Unknown/Custom antibot detection
- 🖥️ **Technology detection** — React, Vue, Angular, Next.js, Nuxt, Svelte, WordPress, Shopify, Drupal, Joomla, Wix, Webflow
- ⚡ **JS requirement detection** — know before you write whether `requests` is enough or Playwright is needed
- 🌐 **API endpoint discovery** — via CSP headers, inline scripts, and XHR/Fetch interception (Playwright mode)
- 🤖 **robots.txt parser** — URL extraction with common path variants (`/robot.txt`, `/robots.txt`)
- 🗺️ **Sitemap detection** — via robots.txt or direct probe (`/sitemap.xml`, `/sitemaps.xml`...)
- 🔐 **Login wall detection** — form, redirect, button, OAuth
- 📸 **Screenshot** — capture the page as seen by the browser (Playwright mode)
- 🚫 **Blocked by antibot** — if the site blocks you, all fields return `"blocked by antibot"` instantly
- 🌍 **Multi-language output** — fr, en, es, br
- 📄 **JSON & TXT export** — machine-readable or human-readable

---

## Engines

| Feature | `curl` | `playwright` |
|---|---|---|
| Speed | ⚡ Fast | 🐢 Slower |
| JS execution | ❌ | ✅ |
| XHR/Fetch API detection | ❌ | ✅ |
| Screenshot | ❌ | ✅ |
| Bot bypass | Partial | Better with `headless=False` |

---

## Anti-bot detection

When the site blocks you (403, captcha page), scrapalyser reports which antibot is responsible
and marks all other fields as `"blocked by antibot"` — so you know exactly what you're up
against before writing anything.

Supported:
| Solution | Detection method |
|---|---|
| Cloudflare / Turnstile | `cf-ray` header, `__cf_bm` cookie |
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

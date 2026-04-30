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
  "scanned_at": "2026-04-30T12:32:00Z",
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
        Scanné le : 2026-04-30T12:32:00Z
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

- 🛡️ **Anti-bot detection** — Cloudflare, DataDome, PerimeterX, Akamai, Kasada, reCAPTCHA, hCaptcha
- 🖥️ **Technology detection** — React, Vue, Angular, Next.js, Nuxt, Svelte, WordPress, Shopify, Drupal, Joomla, Wix, Webflow
- ⚡ **JS requirement detection** — know before you write whether `requests` is enough or Playwright is needed
- 🌐 **API endpoint discovery** — via CSP headers, inline scripts, and XHR/Fetch interception (Playwright mode)
- 🤖 **robots.txt parser** — URL extraction with common path variants
- 🗺️ **Sitemap detection** — via robots.txt or direct probe
- 🔐 **Login wall detection** — form, redirect, button, OAuth
- 📸 **Screenshot** — capture the page as seen by the browser (Playwright mode)
- 🌍 **Multi-language output** — fr, en, es, br
- 📄 **JSON & TXT export** — machine-readable or human-readable

---

## Engines

| Feature | `curl` | `playwright` |
|---|---|---|
| Speed | Fast | Slower |
| JS execution | ❌ | ✅ |
| XHR/Fetch API detection | ❌ | ✅ |
| Screenshot | ❌ | ✅ |
| Bot detection bypass | Partial | Better with `headless=False` |

---

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Commit your changes
4. Open a pull request

---

## License

MIT — see [LICENSE](LICENSE).

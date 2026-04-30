import asyncio
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from .modules import antibot, technology, js_check, login_wall, robots
from .modules.api import _is_excluded, EXCLUDED_EXTENSIONS
from .output import json_output, txt_output

BLOCKED = "blocked by antibot"

CAPTCHA_MARKERS = [
    "window._cf_chl_opt", "cf-browser-verification", "challenge-platform",
    "just a moment", "checking your browser", "google.com/recaptcha",
    "hcaptcha.com/1/api.js", "window._pxAppId", "_pxCaptcha",
    "datadome.co/captcha", "please enable js and disable any ad blocker",
    "var dd={'rt'", "access denied", "bot verification", "security check",
]

BLOCKED_STATUS_CODES = {403, 401, 429, 503}

XHR_TYPES = {"xhr", "fetch"}


def _is_captcha_page(html: str) -> bool:
    html_lower = html.lower()
    return any(m.lower() in html_lower for m in CAPTCHA_MARKERS)


def _is_api_endpoint(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if _is_excluded(parsed.netloc):
            return False
        path = parsed.path.lower()
        if any(path.endswith(ext) for ext in EXCLUDED_EXTENSIONS):
            return False
        return True
    except Exception:
        return False


async def _scan_playwright_async(
    url: str,
    headless: bool = True,
    output: str = "json",
    lang: str = "en",
    save: Optional[str] = None,
    screenshot: Optional[str] = None,
) -> Any:
    from playwright.async_api import async_playwright
    from curl_cffi.requests import AsyncSession

    scanned_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    api_endpoints: list[str] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        def on_request(request):
            if request.resource_type in XHR_TYPES:
                req_url = request.url
                if _is_api_endpoint(req_url) and req_url not in api_endpoints:
                    api_endpoints.append(req_url)

        page.on("request", on_request)

        try:
            pw_response = await page.goto(url, wait_until="networkidle", timeout=20000)
        except Exception:
            try:
                pw_response = await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            except Exception:
                pw_response = None
            await asyncio.sleep(3)

        html = await page.content()
        status_code = pw_response.status if pw_response else 0
        headers = dict(pw_response.headers) if pw_response else {}
        cookies = {c["name"].lower(): c["value"] for c in await context.cookies()}

        screenshot_bytes = await page.screenshot(full_page=False)
        if screenshot:
            with open(screenshot, "wb") as f:
                f.write(screenshot_bytes)

        await browser.close()

    blocked = status_code in BLOCKED_STATUS_CODES or _is_captcha_page(html)

    class FakeResponse:
        def __init__(self, h, c, s, u):
            self.headers = h
            self.cookies = c
            self.status_code = s
            self.url = u

    fake_resp = FakeResponse(headers, cookies, status_code, url)

    antibot_result = await antibot.detect(fake_resp, html)

    if blocked:
        report: dict[str, Any] = {
            "url": url,
            "scanned_at": scanned_at,
            "status_code": status_code,
            "engine": "playwright",
            "antibot": antibot_result,
            "technology": BLOCKED,
            "js_required": BLOCKED,
            "api": BLOCKED,
            "robots_txt": BLOCKED,
            "sitemap": BLOCKED,
            "login_wall": BLOCKED,
            "screenshot": screenshot if screenshot else None,
        }
    else:
        tech_result, js_result, login_result = await asyncio.gather(
            technology.detect(fake_resp, html),
            js_check.detect(url, html),
            login_wall.detect(fake_resp, html),
        )

        async with AsyncSession(impersonate="chrome") as session:
            robots_result = await robots.detect(url, session)

        report = {
            "url": url,
            "scanned_at": scanned_at,
            "status_code": status_code,
            "engine": "playwright",
            "antibot": antibot_result,
            "technology": tech_result,
            "js_required": True if (tech_result or {}).get("type") in JS_FRAMEWORKS else (js_result.get("js_required") if js_result else None),
            "api": {
                "detected": len(api_endpoints) > 0,
                "endpoints": api_endpoints,
            },
            "robots_txt": robots_result.get("robots_txt") if robots_result else None,
            "sitemap": robots_result.get("sitemap") if robots_result else None,
            "login_wall": login_result,
            "screenshot": screenshot if screenshot else None,
        }

    if output == "txt":
        rendered = txt_output.render(report, lang)
        if save:
            txt_output.save(report, save, lang)
        print(rendered)
        return rendered
    else:
        if save:
            json_output.save(report, save)
        return report


JS_FRAMEWORKS = {"Next.js", "Nuxt", "React", "Vue", "Angular", "Svelte"}

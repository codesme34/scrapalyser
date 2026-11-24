import asyncio
import re
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from .modules import antibot, technology, js_check, login_wall, robots, embedded_data, rate_limit
from .modules.api import _is_excluded, EXCLUDED_EXTENSIONS
from .blocking import is_blocked, diagnose

BLOCKED = "blocked by antibot"

XHR_TYPES = {"xhr", "fetch"}


async def _read_content(page: Any, tries: int = 5) -> str:
    """page.content() fails while the page navigates (a solved challenge reloading):
    wait for the new page instead of giving up."""
    for _ in range(tries):
        try:
            return await page.content()
        except Exception as e:
            if "navigating" not in str(e):
                raise
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass
    return await page.content()


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
    headless: bool = False,
    screenshot: Optional[str] = None,
    proxy: Any = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    from playwright.async_api import async_playwright
    from curl_cffi.requests import AsyncSession

    scanned_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    api_endpoints: list[str] = []

    async with async_playwright() as p:
        # Hides navigator.webdriver natively (a JS override would itself be detectable)
        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
            proxy=proxy.for_playwright() if proxy else None,
        )
        # Keep the real browser's user agent: a forced one (other OS / version)
        # contradicts the rest of the fingerprint. Headless mode only needs
        # "HeadlessChrome" renamed to "Chrome".
        user_agent = None
        if headless:
            probe = await browser.new_page()
            real_ua = await probe.evaluate("navigator.userAgent")
            await probe.close()
            # Real Chrome reports a reduced version ("Chrome/159.0.0.0")
            user_agent = re.sub(r"HeadlessChrome/(\d+)[\d.]*", r"Chrome/\1.0.0.0", real_ua)
        context = await browser.new_context(user_agent=user_agent)
        page = await context.new_page()

        def on_request(request):
            if request.resource_type in XHR_TYPES:
                req_url = request.url
                if _is_api_endpoint(req_url) and req_url not in api_endpoints:
                    api_endpoints.append(req_url)

        page.on("request", on_request)

        # Challenge pages (Cloudflare, Fastly...) reload the page once solved:
        # keep the last main document response, not the challenge's
        documents: list = []

        def on_response(response):
            if response.request.is_navigation_request() and response.frame == page.main_frame:
                documents.append(response)

        page.on("response", on_response)

        # Load the page once, then give it a few seconds to fire its API calls.
        # (Navigating a second time after a networkidle timeout doubled the wait.)
        load_error = "no response"
        try:
            pw_response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
        except Exception as e:
            pw_response = None
            load_error = str(e).splitlines()[0]
        if pw_response is not None:
            try:
                await page.wait_for_load_state("networkidle", timeout=min(timeout, 10) * 1000)
            except Exception:
                pass  # pages with endless trackers never go idle: keep what we have

        if pw_response is None:
            # Nothing was loaded (bad proxy, DNS, network): not a pass
            await browser.close()
            raise RuntimeError(f"Playwright could not load {url}: {load_error}")

        html = await _read_content(page)
        if documents:
            pw_response = documents[-1]
        # HTML as sent by the server, before any JS ran: tells if JS is needed
        try:
            raw_html = await pw_response.text()
        except Exception:
            raw_html = None
        final_url = page.url
        status_code = pw_response.status if pw_response else 0
        headers = dict(pw_response.headers) if pw_response else {}
        # Only the site's cookies: ads and widgets set their own (e.g. __cf_bm from a
        # third-party widget on Cloudflare) and would be mistaken for the site's antibot
        cookies = {c["name"].lower(): c["value"] for c in await context.cookies(final_url)}

        screenshot_bytes = await page.screenshot(full_page=False)
        if screenshot:
            with open(screenshot, "wb") as f:
                f.write(screenshot_bytes)

        await browser.close()

    blocked = is_blocked(status_code, headers, html)

    class FakeResponse:
        def __init__(self, h, c, s, u):
            self.headers = h
            self.cookies = c
            self.status_code = s
            self.url = u

    fake_resp = FakeResponse(headers, cookies, status_code, final_url)

    antibot_result = await antibot.detect(fake_resp, html)

    if blocked:
        report: dict[str, Any] = {
            "url": url,
            "scanned_at": scanned_at,
            "status_code": status_code,
            "engine": "playwright",
            "antibot": antibot_result,
            "blocking": diagnose(status_code, headers, html),
            "rate_limit": rate_limit.detect(headers),
            "technology": BLOCKED,
            "js_required": BLOCKED,
            "api": BLOCKED,
            "embedded_data": BLOCKED,
            "robots_txt": BLOCKED,
            "sitemap": BLOCKED,
            "login_wall": BLOCKED,
            "screenshot": screenshot if screenshot else None,
        }
    else:
        tech_result, js_result, login_result = await asyncio.gather(
            technology.detect(fake_resp, html),
            js_check.detect(url, raw_html if raw_html is not None else html),
            login_wall.detect(fake_resp, html, requested_url=url),
        )

        async with AsyncSession(impersonate="chrome", proxy=proxy.for_curl() if proxy else None) as session:
            robots_result = await robots.detect(url, session, timeout=min(timeout, 15))

        report = {
            "url": url,
            "scanned_at": scanned_at,
            "status_code": status_code,
            "engine": "playwright",
            "antibot": antibot_result,
            "blocking": None,
            "rate_limit": rate_limit.detect(headers),
            "technology": tech_result,
            "js_required": js_result.get("js_required") if js_result else None,
            "api": {
                "detected": len(api_endpoints) > 0,
                "endpoints": api_endpoints,
            },
            # Raw server HTML: the data a scraper gets without running JS
            "embedded_data": embedded_data.detect(raw_html if raw_html is not None else html),
            "robots_txt": robots_result.get("robots_txt") if robots_result else None,
            "sitemap": robots_result.get("sitemap") if robots_result else None,
            "login_wall": login_result,
            "screenshot": screenshot if screenshot else None,
        }

    return report


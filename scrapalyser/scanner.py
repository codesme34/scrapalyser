import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

from curl_cffi.requests import AsyncSession

from .modules import antibot, technology, js_check, api, robots, login_wall
from .output import json_output, txt_output
from .blocking import is_blocked, diagnose
from .proxy import Proxy, parse_proxy

BLOCKED = "blocked by antibot"


async def _scan_curl(url: str, proxy: Optional[Proxy] = None) -> dict[str, Any]:
    async with AsyncSession(impersonate="chrome", proxy=proxy.for_curl() if proxy else None) as session:
        try:
            response = await session.get(url, timeout=15)
            html = response.text
        except Exception as e:
            msg = proxy.hide(str(e)) if proxy else str(e)
            if proxy and "407" in msg:
                msg = "proxy refused the credentials (HTTP 407): check user / password"
            raise RuntimeError(f"Failed to fetch {url}: {msg}") from None

        scanned_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        if is_blocked(response.status_code, response.headers, html):
            antibot_result = await antibot.detect(response, html)
            report: dict[str, Any] = {
                "url": url,
                "scanned_at": scanned_at,
                "status_code": response.status_code,
                "engine": "curl",
                "antibot": antibot_result,
                "blocking": diagnose(response.status_code, response.headers, html),
                "technology": BLOCKED,
                "js_required": BLOCKED,
                "api": BLOCKED,
                "robots_txt": BLOCKED,
                "sitemap": BLOCKED,
                "login_wall": BLOCKED,
            }
        else:
            antibot_result, tech_result, js_result, robots_result, login_result, api_result = (
                await asyncio.gather(
                    antibot.detect(response, html),
                    technology.detect(response, html),
                    js_check.detect(url, html),
                    robots.detect(url, session),
                    login_wall.detect(response, html, requested_url=url),
                    api.detect(html, response),
                )
            )
            report = {
                "url": url,
                "scanned_at": scanned_at,
                "status_code": response.status_code,
                "engine": "curl",
                "antibot": antibot_result,
                "blocking": None,
                "technology": tech_result,
                # Measured on the HTML itself: Next.js / Nuxt pages are often
                # server-rendered and complete without JS
                "js_required": js_result.get("js_required") if js_result else None,
                "api": api_result,
                "robots_txt": robots_result.get("robots_txt") if robots_result else None,
                "sitemap": robots_result.get("sitemap") if robots_result else None,
                "login_wall": login_result,
            }
    return report


def _attempt(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "engine": report["engine"],
        "status_code": report.get("status_code"),
        "passed": report.get("blocking") is None,
        "blocking": report.get("blocking"),
    }


async def _scan_playwright(url: str, headless: bool, screenshot: Optional[str], proxy: Optional[Proxy] = None) -> dict[str, Any]:
    from .playwright_scanner import _scan_playwright_async
    return await _scan_playwright_async(url, headless=headless, screenshot=screenshot, proxy=proxy)


async def _scan_auto(url: str, headless: bool, screenshot: Optional[str], proxy: Optional[Proxy] = None) -> dict[str, Any]:
    """curl_cffi first; if it is blocked, Playwright. The first engine that passes wins."""
    curl_report: Optional[dict[str, Any]] = None
    attempts: list[dict[str, Any]] = []
    try:
        curl_report = await _scan_curl(url, proxy)
        attempts.append(_attempt(curl_report))
        if curl_report["blocking"] is None:
            curl_report["attempts"] = attempts
            return curl_report
    except RuntimeError as e:
        attempts.append({"engine": "curl", "status_code": None, "passed": False, "error": str(e)})

    try:
        pw_report = await _scan_playwright(url, headless, screenshot, proxy)
    except Exception as e:
        if proxy:
            e = RuntimeError(proxy.hide(str(e)))
        # Playwright missing or its browser not installed: keep the curl result
        attempts.append({"engine": "playwright", "status_code": None, "passed": False, "error": str(e).splitlines()[0] if str(e) else type(e).__name__})
        if curl_report is None:
            # "from None": the original traceback could show the proxy password
            details = " | ".join(f"{a['engine']}: {a['error']}" for a in attempts)
            raise RuntimeError(f"Failed to fetch {url} with curl_cffi and Playwright ({details})") from None
        curl_report["attempts"] = attempts
        return curl_report

    attempts.append(_attempt(pw_report))
    pw_report["attempts"] = attempts
    return pw_report


def _finish(report: dict[str, Any], output: str, lang: str, save: Optional[str]) -> Any:
    if output == "txt":
        rendered = txt_output.render(report, lang)
        if save:
            txt_output.save(report, save, lang)
        print(rendered)
        return rendered
    if save:
        json_output.save(report, save)
    return report


def scan(
    url: str,
    output: str = "json",
    lang: str = "en",
    save: Optional[str] = None,
    engine: str = "auto",
    headless: bool = False,
    screenshot: Optional[str] = None,
    proxy: Optional[str] = None,
) -> Any:
    """Scan a website before scraping it.

    proxy: "http://USER:PASSWORD@HOST:PORT" (also accepted: USER:PASSWORD@HOST:PORT,
    HOST:PORT:USER:PASSWORD, USER:PASSWORD:HOST:PORT, HOST:PORT). Used by both engines.
    """
    parsed_proxy = parse_proxy(proxy) if proxy else None
    if engine == "curl":
        report = asyncio.run(_scan_curl(url, parsed_proxy))
        report["attempts"] = [_attempt(report)]
    elif engine == "playwright":
        report = asyncio.run(_scan_playwright(url, headless, screenshot, parsed_proxy))
        report["attempts"] = [_attempt(report)]
    elif engine == "auto":
        report = asyncio.run(_scan_auto(url, headless, screenshot, parsed_proxy))
    else:
        raise ValueError(f'engine must be "auto", "curl" or "playwright", not {engine!r}')
    # Server only: the report may be saved or shared, credentials stay out
    report["proxy"] = parsed_proxy.server if parsed_proxy else None
    return _finish(report, output, lang, save)

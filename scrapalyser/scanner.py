import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

from curl_cffi.requests import AsyncSession

from .modules import antibot, technology, js_check, api, robots, login_wall
from .output import json_output, txt_output

BLOCKED = "blocked by antibot"

JS_FRAMEWORKS = {"Next.js", "Nuxt", "React", "Vue", "Angular", "Svelte"}

BLOCKED_STATUS_CODES = {403, 401, 429, 503}

CAPTCHA_MARKERS = [
    # Cloudflare
    "window._cf_chl_opt",
    "cf-browser-verification",
    "challenge-platform",
    "just a moment",
    "checking your browser",
    # reCAPTCHA / hCaptcha inline challenge
    "google.com/recaptcha",
    "hcaptcha.com/1/api.js",
    # PerimeterX
    "window._pxAppId",
    "_pxCaptcha",
    # DataDome
    "datadome.co/captcha",
    "please enable js and disable any ad blocker",
    "var dd={'rt'",
    # Generic
    "access denied",
    "bot verification",
    "security check",
]


def _is_blocked(response: Any) -> bool:
    return response.status_code in BLOCKED_STATUS_CODES


def _is_captcha_page(html: str) -> bool:
    html_lower = html.lower()
    return any(marker.lower() in html_lower for marker in CAPTCHA_MARKERS)


async def _scan_async(
    url: str,
    output: str = "json",
    lang: str = "en",
    save: Optional[str] = None,
) -> Any:
    async with AsyncSession(impersonate="chrome") as session:
        try:
            response = await session.get(url, timeout=15)
            html = response.text
        except Exception as e:
            raise RuntimeError(f"Failed to fetch {url}: {e}") from e

        scanned_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        if _is_blocked(response) or _is_captcha_page(html):
            antibot_result = await antibot.detect(response, html)
            report: dict[str, Any] = {
                "url": url,
                "scanned_at": scanned_at,
                "status_code": response.status_code,
                "engine": "curl",
                "antibot": antibot_result,
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
                    login_wall.detect(response, html),
                    api.detect(html, response),
                )
            )
            report = {
                "url": url,
                "scanned_at": scanned_at,
                "status_code": response.status_code,
                "engine": "curl",
                "antibot": antibot_result,
                "technology": tech_result,
                "js_required": True if (tech_result or {}).get("type") in JS_FRAMEWORKS else (js_result.get("js_required") if js_result else None),
                "api": api_result,
                "robots_txt": robots_result.get("robots_txt") if robots_result else None,
                "sitemap": robots_result.get("sitemap") if robots_result else None,
                "login_wall": login_result,
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


def scan(
    url: str,
    output: str = "json",
    lang: str = "en",
    save: Optional[str] = None,
    engine: str = "curl",
    headless: bool = True,
    screenshot: Optional[str] = None,
) -> Any:
    if engine == "playwright":
        from .playwright_scanner import _scan_playwright_async
        return asyncio.run(_scan_playwright_async(url, headless=headless, output=output, lang=lang, save=save, screenshot=screenshot))
    return asyncio.run(_scan_async(url, output=output, lang=lang, save=save))

import asyncio
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Iterable, Optional, Union
from urllib.parse import urlparse

from curl_cffi.requests import AsyncSession

from .modules import antibot, technology, js_check, api, robots, login_wall, embedded_data, rate_limit
from .output import json_output, txt_output
from .blocking import is_blocked, diagnose
from .proxy import Proxy, parse_proxy

BLOCKED = "blocked by antibot"

DEFAULT_TIMEOUT = 30.0
# robots.txt / sitemap checks are small files: no need to wait as long as for the page
SIDE_TIMEOUT_MAX = 15.0


async def _scan_curl(url: str, proxy: Optional[Proxy] = None, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]:
    async with AsyncSession(impersonate="chrome", proxy=proxy.for_curl() if proxy else None) as session:
        try:
            response = await session.get(url, timeout=timeout)
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
                "rate_limit": rate_limit.detect(response.headers),
                "technology": BLOCKED,
                "js_required": BLOCKED,
                "api": BLOCKED,
                "embedded_data": BLOCKED,
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
                    robots.detect(url, session, timeout=min(timeout, SIDE_TIMEOUT_MAX)),
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
                "rate_limit": rate_limit.detect(response.headers),
                "technology": tech_result,
                # Measured on the HTML itself: Next.js / Nuxt pages are often
                # server-rendered and complete without JS
                "js_required": js_result.get("js_required") if js_result else None,
                "api": api_result,
                "embedded_data": embedded_data.detect(html),
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


async def _scan_playwright(url: str, headless: bool, screenshot: Optional[str], proxy: Optional[Proxy] = None, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]:
    from .playwright_scanner import _scan_playwright_async
    return await _scan_playwright_async(url, headless=headless, screenshot=screenshot, proxy=proxy, timeout=timeout)


async def _scan_auto(url: str, headless: bool, screenshot: Optional[str], proxy: Optional[Proxy] = None, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]:
    """curl_cffi first; if it is blocked, Playwright. The first engine that passes wins."""
    curl_report: Optional[dict[str, Any]] = None
    attempts: list[dict[str, Any]] = []
    try:
        curl_report = await _scan_curl(url, proxy, timeout)
        attempts.append(_attempt(curl_report))
        if curl_report["blocking"] is None:
            curl_report["attempts"] = attempts
            return curl_report
    except RuntimeError as e:
        attempts.append({"engine": "curl", "status_code": None, "passed": False, "error": str(e)})

    try:
        pw_report = await _scan_playwright(url, headless, screenshot, proxy, timeout)
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


ENGINES = ("auto", "curl", "playwright")


def _build_report(
    url: str,
    engine: str,
    headless: bool,
    screenshot: Optional[str],
    proxy: Optional[Proxy],
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    try:
        if engine == "curl":
            report = asyncio.run(_scan_curl(url, proxy, timeout))
            report["attempts"] = [_attempt(report)]
        elif engine == "playwright":
            report = asyncio.run(_scan_playwright(url, headless, screenshot, proxy, timeout))
            report["attempts"] = [_attempt(report)]
        else:
            report = asyncio.run(_scan_auto(url, headless, screenshot, proxy, timeout))
    except Exception as e:
        if proxy:
            # "from None": the original traceback could show the proxy password
            raise RuntimeError(proxy.hide(str(e))) from None
        raise
    # Server only: the report may be saved or shared, credentials stay out
    report["proxy"] = proxy.server if proxy else None
    return report


def _check_engine(engine: str) -> None:
    if engine not in ENGINES:
        raise ValueError(f'engine must be "auto", "curl" or "playwright", not {engine!r}')


def _check_timeout(timeout: Any) -> float:
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError(f"timeout must be a number of seconds > 0, not {timeout!r}")
    return float(timeout)


def scan(
    url: Union[str, Iterable[str]],
    output: str = "json",
    lang: str = "en",
    save: Optional[str] = None,
    engine: str = "auto",
    headless: bool = False,
    screenshot: Optional[str] = None,
    proxy: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT,
    workers: int = 4,
    save_dir: Optional[str] = None,
) -> Any:
    """Scan a website before scraping it.

    url: one URL -> one report, or a list of URLs -> a list of reports (same order).
    workers: with a list, how many sites are scanned at the same time (default 4).
    save_dir: with a list, a folder to write one report per site.
    proxy: "http://USER:PASSWORD@HOST:PORT" (also accepted: USER:PASSWORD@HOST:PORT,
    HOST:PORT:USER:PASSWORD, USER:PASSWORD:HOST:PORT, HOST:PORT). Used by both engines.
    timeout: seconds to wait for the page (default 30). Raise it for slow sites or proxies.
    """
    _check_workers(workers)
    if not isinstance(url, str):
        if save or screenshot:
            raise ValueError("save and screenshot take one URL; with a list of URLs, use save_dir")
        return scan_many(url, workers=workers, output=output, lang=lang, save_dir=save_dir,
                         engine=engine, headless=headless, proxy=proxy, timeout=timeout)
    _check_engine(engine)
    timeout = _check_timeout(timeout)
    parsed_proxy = parse_proxy(proxy) if proxy else None
    report = _build_report(url, engine, headless, screenshot, parsed_proxy, timeout)
    if save_dir and not save:
        os.makedirs(save_dir, exist_ok=True)
        save = os.path.join(save_dir, _file_name(1, url, "txt" if output == "txt" else "json"))
    return _finish(report, output, lang, save)


def _check_workers(workers: Any) -> None:
    if isinstance(workers, bool) or not isinstance(workers, int) or workers < 1:
        raise ValueError(f"workers must be an integer >= 1, not {workers!r}")


def _file_name(index: int, url: str, ext: str) -> str:
    host = urlparse(url).hostname or "site"
    return f"{index:03d}_{re.sub(r'[^a-zA-Z0-9.-]', '_', host)}.{ext}"


def scan_many(
    urls: Iterable[str],
    workers: int = 4,
    output: str = "json",
    lang: str = "en",
    save_dir: Optional[str] = None,
    engine: str = "auto",
    headless: bool = False,
    proxy: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> list[Any]:
    """Scan several websites in parallel. Same as scan() with a list of URLs.

    workers: how many scans run at the same time (1 = one after the other).
    Each Playwright scan opens its own browser (~200-300 MB of RAM).
    Use workers on *different* sites: many parallel scans of the same site get you blocked.

    Returns one result per URL, in the same order as `urls`. A site that fails
    does not stop the others: its result is {"url": ..., "error": ...}.
    save_dir: optional folder, one file per site (001_example.com.json, ...).
    Other options are the same as scan().
    """
    urls = list(urls)
    _check_workers(workers)
    _check_engine(engine)
    timeout = _check_timeout(timeout)
    parsed_proxy = parse_proxy(proxy) if proxy else None  # fail fast on a bad format

    def one(url: str) -> dict[str, Any]:
        try:
            return _build_report(url, engine, headless, None, parsed_proxy, timeout)
        except Exception as e:
            return {"url": url, "error": f"{type(e).__name__}: {e}"}

    with ThreadPoolExecutor(max_workers=min(workers, max(len(urls), 1))) as pool:
        reports = list(pool.map(one, urls))  # map keeps the order of urls

    if save_dir:
        os.makedirs(save_dir, exist_ok=True)

    results: list[Any] = []
    for i, report in enumerate(reports, 1):
        if output == "txt":
            if "error" in report:
                rendered = f"[ERROR] {report['url']}: {report['error']}"
            else:
                rendered = txt_output.render(report, lang)
            print(rendered)
            result: Any = rendered
        else:
            result = report
        if save_dir:
            ext = "txt" if output == "txt" else "json"
            path = os.path.join(save_dir, _file_name(i, report["url"], ext))
            with open(path, "w", encoding="utf-8") as f:
                f.write(rendered if output == "txt" else json_output.render(report))
        results.append(result)
    return results

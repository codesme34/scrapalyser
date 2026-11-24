import asyncio
import re
from typing import Any, Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

ROBOTS_PATHS = ["/robots.txt", "/robot.txt"]

SITEMAP_PATHS = [
    "/sitemap.xml",
    "/sitemaps.xml",
    "/site-map.xml",
    "/sitemap_index.xml",
    "/sitemap-index.xml",
]

# Sitemaps declared in robots.txt that are checked (big sites declare dozens)
MAX_SITEMAPS_CHECKED = 10
# Only the start of a sitemap is read: enough to recognise it, sitemaps can weigh tens of MB
SITEMAP_PEEK_BYTES = 2048
SITEMAP_MARKERS = (b"<urlset", b"<sitemapindex", b"<?xml")

SITEMAP_LINE = re.compile(r"^\s*Sitemap:\s*(\S+)", re.MULTILINE | re.IGNORECASE)


def _base_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _path_of(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    return f"{path}?{parsed.query}" if parsed.query else path


def _rules(robots_text: str, url: str) -> dict:
    """Is the scanned page allowed for any bot ("*"), and the Crawl-delay asked."""
    parser = RobotFileParser()
    parser.parse(robots_text.splitlines())
    try:
        allowed: Optional[bool] = parser.can_fetch("*", _path_of(url))
    except Exception:
        allowed = None
    delay = parser.crawl_delay("*")
    return {"allowed": allowed, "crawl_delay": float(delay) if delay is not None else None}


async def _is_sitemap(session: Any, url: str, timeout: float) -> bool:
    """The URL answers 200 and starts like a sitemap (or is a .gz file)."""
    resp = None
    try:
        resp = await session.get(url, timeout=timeout, stream=True)
        if resp.status_code != 200:
            return False
        ctype = resp.headers.get("content-type", "").lower()
        if url.lower().endswith(".gz") or "gzip" in ctype:
            return True
        head = b""
        async for chunk in resp.aiter_content():
            head += chunk
            if len(head) >= SITEMAP_PEEK_BYTES:
                break
        head = head.lstrip().lower()
        return "xml" in ctype or any(m in head for m in SITEMAP_MARKERS)
    except Exception:
        return False
    finally:
        if resp is not None:
            try:
                await resp.aclose()
            except Exception:
                pass


async def detect(url: str, session: Any, timeout: float = 10) -> Optional[dict]:
    try:
        base = _base_url(url)
        robots_result: dict = {"found": False, "url": None, "allowed": None, "crawl_delay": None}
        declared: list[str] = []

        for path in ROBOTS_PATHS:
            try:
                resp = await session.get(urljoin(base, path), timeout=timeout)
            except Exception:
                continue
            if resp.status_code == 200 and resp.text.strip():
                robots_result = {"found": True, "url": urljoin(base, path), **_rules(resp.text, url)}
                for match in SITEMAP_LINE.finditer(resp.text):
                    sitemap_url = urljoin(base, match.group(1).strip())
                    if sitemap_url not in declared:
                        declared.append(sitemap_url)
                break

        # Sitemaps declared in robots.txt first, the usual paths otherwise
        candidates = declared[:MAX_SITEMAPS_CHECKED] or [urljoin(base, p) for p in SITEMAP_PATHS]
        checks = await asyncio.gather(*(_is_sitemap(session, c, timeout) for c in candidates))
        working = [c for c, ok in zip(candidates, checks) if ok]
        if declared and not working:
            # robots.txt points to dead sitemaps: try the usual paths anyway
            usual = [urljoin(base, p) for p in SITEMAP_PATHS]
            checks = await asyncio.gather(*(_is_sitemap(session, c, timeout) for c in usual))
            working = [c for c, ok in zip(usual, checks) if ok][:1]
        elif not declared:
            working = working[:1]  # the usual paths often point to the same file

        sitemap_result = {
            "found": bool(working),
            "url": working[0] if working else None,  # kept for compatibility
            "urls": working,
            "declared_in_robots": len(declared),
        }
        return {"robots_txt": robots_result, "sitemap": sitemap_result}
    except Exception:
        return None

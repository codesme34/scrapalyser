from urllib.parse import urljoin, urlparse
from typing import Any
import re


ROBOTS_PATHS = ["/robots.txt", "/robot.txt"]

SITEMAP_PATHS = [
    "/sitemap.xml",
    "/sitemaps.xml",
    "/site-map.xml",
    "/sitemap_index.xml",
    "/sitemap-index.xml",
]


def _base_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


async def detect(url: str, session: Any) -> dict:
    try:
        base = _base_url(url)
        robots_result = {"found": False, "url": None}
        sitemap_result = {"found": False, "url": None}
        sitemap_found_in_robots = False

        # Try all robots paths
        for path in ROBOTS_PATHS:
            try:
                resp = await session.get(urljoin(base, path), timeout=10)
                if resp.status_code == 200 and resp.text.strip():
                    robots_result = {"found": True, "url": urljoin(base, path)}

                    match = re.search(r"^Sitemap:\s*(.+)$", resp.text, re.MULTILINE | re.IGNORECASE)
                    if match:
                        sitemap_result = {"found": True, "url": urljoin(base, "/sitemap.xml")}
                        sitemap_found_in_robots = True
                    break
            except Exception:
                continue

        # Try all sitemap paths if not found via robots
        if not sitemap_found_in_robots:
            for path in SITEMAP_PATHS:
                try:
                    resp = await session.get(urljoin(base, path), timeout=10)
                    if resp.status_code == 200 and "xml" in resp.headers.get("content-type", "").lower():
                        sitemap_result = {"found": True, "url": urljoin(base, path)}
                        break
                except Exception:
                    continue

        return {"robots_txt": robots_result, "sitemap": sitemap_result}
    except Exception:
        return None

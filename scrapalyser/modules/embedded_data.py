"""Data already present in the HTML as JSON: when it is there, a scraper can read
it directly instead of parsing the page (and often without running JavaScript)."""

import json
import re
from typing import Optional

from bs4 import BeautifulSoup

# <script id="..."> holding the page data, by framework
SCRIPT_IDS = {
    "__NEXT_DATA__": "Next.js (__NEXT_DATA__)",
    "__NUXT_DATA__": "Nuxt (__NUXT_DATA__)",
    "__APOLLO_STATE__": "Apollo GraphQL cache",
    "__REMIX_CONTEXT__": "Remix context",
    "ng-state": "Angular transfer state",
    "serverApp-state": "Angular transfer state",
}

# window.X = {...} assignments in inline scripts
WINDOW_VARS = {
    "__NUXT__": "Nuxt (window.__NUXT__)",
    "__INITIAL_STATE__": "window.__INITIAL_STATE__",
    "__PRELOADED_STATE__": "Redux (window.__PRELOADED_STATE__)",
    "__APOLLO_STATE__": "Apollo GraphQL cache (window.__APOLLO_STATE__)",
    "__remixContext": "Remix (window.__remixContext)",
    "__INITIAL_DATA__": "window.__INITIAL_DATA__",
    "__DATA__": "window.__DATA__",
}
WINDOW_VAR = re.compile(r"(?:window\.|self\.)?(" + "|".join(map(re.escape, WINDOW_VARS)) + r")\s*=")

# Next.js App Router streams its data in self.__next_f.push(...) calls
NEXT_FLIGHT = re.compile(r"self\.__next_f\.push\(")

# Other JSON blobs below this size are usually config, not page data
MIN_JSON_SIZE = 1000


def _json_ld_types(text: str) -> list[str]:
    try:
        data = json.loads(text)
    except Exception:
        return []
    items = data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []
    types: list[str] = []
    for item in items:
        if isinstance(item, dict):
            t = item.get("@type")
            for name in t if isinstance(t, list) else [t]:
                if isinstance(name, str) and name not in types:
                    types.append(name)
    return types


def detect(html: str) -> Optional[dict]:
    try:
        soup = BeautifulSoup(html, "html.parser")
        sources: list[dict] = []
        seen: set[str] = set()

        def add(kind: str, selector: str, size: int, **extra) -> None:
            if kind in seen:
                return
            seen.add(kind)
            sources.append({"type": kind, "selector": selector, "size": size, **extra})

        # JSON-LD (schema.org): products, offers, articles, breadcrumbs...
        ld_types: list[str] = []
        ld_size = 0
        for tag in soup.find_all("script", type="application/ld+json"):
            text = tag.string or ""
            ld_size += len(text)
            for t in _json_ld_types(text):
                if t not in ld_types:
                    ld_types.append(t)
        if ld_size:
            add("JSON-LD (schema.org)", 'script[type="application/ld+json"]', ld_size, schema_types=ld_types)

        for tag in soup.find_all("script"):
            text = tag.string or ""
            tag_id = tag.get("id") or ""
            if tag_id in SCRIPT_IDS:
                add(SCRIPT_IDS[tag_id], f"script#{tag_id}", len(text))
                continue
            if tag.get("type") == "application/json" and len(text) >= MIN_JSON_SIZE:
                selector = f"script#{tag_id}" if tag_id else 'script[type="application/json"]'
                add(f"JSON in {selector}", selector, len(text))
                continue
            match = WINDOW_VAR.search(text)
            if match:
                add(WINDOW_VARS[match.group(1)], f"window.{match.group(1)}", len(text))
            elif NEXT_FLIGHT.search(text):
                # one push per chunk: count the total size
                if "Next.js App Router (self.__next_f)" in seen:
                    for s in sources:
                        if s["selector"] == "self.__next_f":
                            s["size"] += len(text)
                else:
                    add("Next.js App Router (self.__next_f)", "self.__next_f", len(text))

        return {"detected": bool(sources), "sources": sources}
    except Exception:
        return None

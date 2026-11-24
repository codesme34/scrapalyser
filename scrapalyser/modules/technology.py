from bs4 import BeautifulSoup
from typing import Any
from urllib.parse import urljoin, urlparse


def _site(host: str) -> str:
    # "www.example.co" / "cdn.example.co" -> "example.co"
    return ".".join((host or "").lower().split(".")[-2:])


def _own_assets(soup: BeautifulSoup, page_url: str) -> str:
    """URLs of the scripts and stylesheets served by the site itself."""
    site = _site(urlparse(page_url).hostname or "")
    urls = []
    for tag in soup.find_all(["script", "link"]):
        ref = tag.get("src") or tag.get("href")
        if not ref:
            continue
        full = urljoin(page_url, ref)
        if _site(urlparse(full).hostname or "") == site:
            urls.append(full)
    return " ".join(urls).lower()


SIGNATURES = [
    {"name": "Next.js", "meta": [], "scripts": ["/_next/"], "headers": {"x-powered-by": "next.js"}, "html": ["__NEXT_DATA__"]},
    {"name": "Nuxt", "meta": [], "scripts": ["/_nuxt/"], "headers": {}, "html": ["__nuxt", "__NUXT__"]},
    {"name": "React", "meta": [], "scripts": ["react.development.js", "react.production.min.js"], "headers": {}, "html": ["data-reactroot", "data-reactid"]},
    {"name": "Vue", "meta": [], "scripts": ["vue.js", "vue.min.js", "vue.runtime"], "headers": {}, "html": ["data-v-", "__vue__"]},
    {"name": "Angular", "meta": [], "scripts": ["angular.js", "angular.min.js"], "headers": {}, "html": ["ng-version", "ng-app", "_nghost"]},
    {"name": "Svelte", "meta": [], "scripts": ["svelte/"], "headers": {}, "html": ["svelte-"]},
    # "own_assets": only the site's own files count. A page that links to WordPress
    # sites (search results, aggregators) contains "wp-content" without being WordPress.
    {"name": "WordPress", "meta": [{"name": "generator", "content": "wordpress"}], "scripts": [], "own_assets": ["/wp-content/", "/wp-includes/"], "headers": {"x-pingback": ""}, "html": []},
    {"name": "Shopify", "meta": [], "scripts": ["cdn.shopify.com"], "headers": {"x-shopid": ""}, "html": ["Shopify.theme"]},
    {"name": "Drupal", "meta": [{"name": "generator", "content": "drupal"}], "scripts": ["/sites/default/files/"], "headers": {"x-drupal-cache": ""}, "html": []},
    {"name": "Joomla", "meta": [{"name": "generator", "content": "joomla"}], "scripts": ["/media/jui/"], "headers": {}, "html": []},
    {"name": "Wix", "meta": [], "scripts": ["static.parastorage.com"], "headers": {"x-wix-request-id": ""}, "html": ["wixSite"]},
    {"name": "Webflow", "meta": [{"name": "generator", "content": "webflow"}], "scripts": ["assets.website-files.com"], "headers": {"x-powered-by": "webflow"}, "html": []},
]


async def detect(response: Any, html: str) -> dict:
    try:
        headers = {k.lower(): v.lower() for k, v in response.headers.items()}
        soup = BeautifulSoup(html, "html.parser")
        html_lower = html.lower()
        scripts_src = " ".join(
            tag.get("src", "") for tag in soup.find_all("script") if tag.get("src")
        ).lower()
        own_assets = _own_assets(soup, str(getattr(response, "url", "") or ""))

        for sig in SIGNATURES:
            for meta_check in sig.get("meta", []):
                tag = soup.find("meta", attrs={"name": meta_check["name"]})
                if tag and meta_check["content"].lower() in (tag.get("content", "") or "").lower():
                    return {"type": sig["name"]}

            for header_key, header_val in sig.get("headers", {}).items():
                if header_key in headers:
                    if not header_val or header_val in headers[header_key]:
                        return {"type": sig["name"]}

            for script_pattern in sig.get("scripts", []):
                if script_pattern.lower() in scripts_src:
                    return {"type": sig["name"]}

            for asset_pattern in sig.get("own_assets", []):
                if asset_pattern in own_assets:
                    return {"type": sig["name"]}

            for html_marker in sig.get("html", []):
                if html_marker.lower() in html_lower:
                    return {"type": sig["name"]}

        return {"type": "Static HTML"}
    except Exception:
        return None

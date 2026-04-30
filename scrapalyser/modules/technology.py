from bs4 import BeautifulSoup
from typing import Any


SIGNATURES = [
    {"name": "Next.js", "meta": [], "scripts": ["/_next/"], "headers": {"x-powered-by": "next.js"}, "html": ["__NEXT_DATA__"]},
    {"name": "Nuxt", "meta": [], "scripts": ["/_nuxt/"], "headers": {}, "html": ["__nuxt", "__NUXT__"]},
    {"name": "React", "meta": [], "scripts": ["react.development.js", "react.production.min.js"], "headers": {}, "html": ["data-reactroot", "data-reactid"]},
    {"name": "Vue", "meta": [], "scripts": ["vue.js", "vue.min.js", "vue.runtime"], "headers": {}, "html": ["data-v-", "__vue__"]},
    {"name": "Angular", "meta": [], "scripts": ["angular.js", "angular.min.js"], "headers": {}, "html": ["ng-version", "ng-app", "_nghost"]},
    {"name": "Svelte", "meta": [], "scripts": ["svelte/"], "headers": {}, "html": ["svelte-"]},
    {"name": "WordPress", "meta": [], "scripts": ["/wp-content/", "/wp-includes/"], "headers": {}, "html": ["wp-content", "wp-includes"]},
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

            for html_marker in sig.get("html", []):
                if html_marker.lower() in html_lower:
                    return {"type": sig["name"]}

        return {"type": "Static HTML"}
    except Exception:
        return None

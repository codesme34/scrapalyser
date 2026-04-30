from bs4 import BeautifulSoup
from typing import Any


JS_ROOT_PATTERNS = [
    '<div id="root">',
    '<div id="root"/>',
    '<div id="app">',
    '<div id="app"/>',
    '<div id="__next">',
    '<div id="nuxt">',
]

MIN_CONTENT_LENGTH = 500


async def detect(url: str, html: str) -> dict:
    try:
        soup = BeautifulSoup(html, "html.parser")
        body_text = soup.get_text(strip=True)

        # Page sans aucun script = HTML statique, pas besoin de JS
        scripts = soup.find_all("script")
        if not scripts:
            return {"js_required": False}

        # Détection shell SPA : div root/app vide + peu de contenu texte
        for pattern in JS_ROOT_PATTERNS:
            if pattern.lower() in html.lower():
                if len(body_text) < MIN_CONTENT_LENGTH:
                    return {"js_required": True}

        # Contenu texte très faible mais scripts présents = probablement SPA
        if len(body_text) < MIN_CONTENT_LENGTH and len(scripts) > 3:
            return {"js_required": True}

        return {"js_required": False}
    except Exception:
        return None

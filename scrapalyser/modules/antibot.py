from bs4 import BeautifulSoup
from typing import Any


SIGNATURES = [
    {
        "name": "Cloudflare Turnstile",
        "headers": ["cf-ray"],
        "cookies": ["__cf_bm"],
        "scripts": ["challenges.cloudflare.com/turnstile"],
    },
    {
        "name": "Cloudflare",
        "headers": ["cf-ray"],
        "cookies": ["__cfduid", "__cf_bm"],
        "scripts": [],
    },
    {
        "name": "DataDome",
        "headers": [],
        "cookies": ["dd_at", "datadome"],
        "scripts": ["datadome.co"],
    },
    {
        "name": "PerimeterX",
        "headers": [],
        "cookies": ["_px", "_pxhd", "_pxde"],
        "scripts": ["px.js", "client.perimeterx.net"],
    },
    {
        "name": "Akamai",
        "headers": [],
        "cookies": ["ak_bmsc", "bm_sz"],
        "scripts": [],
    },
    {
        "name": "Kasada",
        "headers": [],
        "cookies": [],
        "scripts": ["kkrta", "kasada.io"],
    },
    {
        "name": "reCAPTCHA",
        "headers": [],
        "cookies": [],
        "scripts": ["google.com/recaptcha"],
    },
    {
        "name": "hCaptcha",
        "headers": [],
        "cookies": [],
        "scripts": ["hcaptcha.com"],
    },
]


async def detect(response: Any, html: str) -> dict:
    try:
        headers = {k.lower(): v for k, v in response.headers.items()}
        cookies = {k.lower(): v for k, v in response.cookies.items()}
        soup = BeautifulSoup(html, "html.parser")
        scripts = " ".join(
            (tag.get("src", "") or tag.string or "")
            for tag in soup.find_all("script")
        ).lower()

        for sig in SIGNATURES:
            header_hit = any(h in headers for h in sig["headers"])
            cookie_hit = any(c in cookies for c in sig["cookies"])
            script_hit = any(s.lower() in scripts for s in sig["scripts"])

            if header_hit or cookie_hit or script_hit:
                return {"detected": True, "name": sig["name"]}

        return {"detected": False, "name": None}
    except Exception:
        return None

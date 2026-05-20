from bs4 import BeautifulSoup
from typing import Any
import re


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
        "headers": ["x-datadome"],
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
        "name": "Imperva",
        "headers": ["x-iinfo", "x-cdn-forward"],
        "cookies": ["incap_ses", "visid_incap", "nlbi_"],
        "scripts": ["imperva.com", "incapsula.com"],
    },
    {
        "name": "Sucuri",
        "headers": ["x-sucuri-id", "x-sucuri-cache"],
        "cookies": [],
        "scripts": ["sucuri.net"],
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

# Headers indicating a custom/unknown protection
CUSTOM_ANTIBOT_HEADERS = [
    "x-distil-cs", "x-distil-uid",
    "x-bot-protection",
    "x-waf",
    "x-shield",
    "x-protected-by",
]

# Suspicious cookie pattern (long, random, unidentified)
SUSPICIOUS_COOKIE_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{20,}$")


def _has_suspicious_cookies(cookies: dict) -> bool:
    known_cookies = {
        "__cf_bm", "__cfduid", "datadome", "dd_at", "_px", "_pxhd",
        "ak_bmsc", "bm_sz", "incap_ses", "visid_incap",
    }
    unknown = [k for k in cookies if k not in known_cookies]
    suspicious = [
        k for k in unknown
        if SUSPICIOUS_COOKIE_PATTERN.match(k) and len(cookies[k]) > 30
    ]
    return len(suspicious) >= 2


def _has_obfuscated_scripts(soup: BeautifulSoup) -> bool:
    for tag in soup.find_all("script"):
        if not tag.get("src") and tag.string:
            content = tag.string.strip()
            if len(content) > 500 and content.count(" ") < len(content) * 0.05:
                return True
    return False


async def detect(response: Any, html: str) -> dict:
    try:
        headers = {k.lower(): v for k, v in response.headers.items()}
        cookies = {k.lower(): v for k, v in response.cookies.items()}
        soup = BeautifulSoup(html, "html.parser")
        scripts = " ".join(
            (tag.get("src", "") or tag.string or "")
            for tag in soup.find_all("script")
        ).lower()

        # Known signatures detection
        for sig in SIGNATURES:
            header_hit = any(h in headers for h in sig["headers"])
            cookie_hit = any(c in cookies for c in sig["cookies"])
            script_hit = any(s.lower() in scripts for s in sig["scripts"])

            if header_hit or cookie_hit or script_hit:
                return {"detected": True, "name": sig["name"]}

        # Custom/unknown detection
        custom_header_hit = any(h in headers for h in CUSTOM_ANTIBOT_HEADERS)
        suspicious_cookies = _has_suspicious_cookies(cookies)
        obfuscated = _has_obfuscated_scripts(soup)

        if custom_header_hit or (suspicious_cookies and obfuscated):
            return {"detected": True, "name": "Unknown / Custom antibot"}

        return {"detected": False, "name": None}
    except Exception:
        return None

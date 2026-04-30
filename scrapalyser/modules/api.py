import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import Any


EXCLUDED_DOMAINS = [
    # Analytics & tracking
    "google-analytics.com", "googletagmanager.com", "analytics.google.com",
    "segment.com", "segment.io", "mixpanel.com", "hotjar.com", "fullstory.com",
    "amplitude.com", "heap.io", "logrocket.com", "clarity.ms",
    "doubleclick.net", "pagead2.googlesyndication.com", "googlesyndication.com",
    # Error monitoring
    "sentry.io", "nr-data.net", "newrelic.com", "bugsnag.com", "rollbar.com",
    "reporting.cdndex.io", "statuspage.io",
    # CDN & fonts
    "fonts.googleapis.com", "fonts.gstatic.com", "cdn.jsdelivr.net",
    "cdnjs.cloudflare.com", "githubassets.com", "static.licdn.com",
    "parastorage.com", "cloudfront.net",
    # Consent & privacy
    "cookielaw.org", "onetrust.com", "geolocation.onetrust.com",
    "privacy-center", "consent.cookiebot.com", "sdk.privacy-center.org",
    # Ads
    "facebook.net", "facebook.com/tr", "adsdk.microsoft.com",
    "adsdkprod.azureedge.net", "bing.net", "moatads.com",
    # Social login
    "accounts.google.com", "appleid.apple.com",
    # Telemetry / beacon
    "protechts.net", "microsoft.com", "edge-auth.microsoft.com",
    "talkingdata.com", "go-mpulse.net", "realytics.io",
    "confidence.dev", "geetest.com", "geevisit.com",
    # Performance monitoring
    "dynatrace.com", "bf.dynatrace.com", "flashb.id", "tn.flashb.id",
    "iadvize.com", "halc.iadvize.com", "static.iadvize.com", "api.iadvize.com",
    "caast.tv", "flagship.io", "cdn.flagship.io", "events.flagship.io",
    "kaminoretail.io", "delivery.kaminoretail.io",
    "acsbapp.com", "eu.acsbapp.com", "eu-cdn.acsbapp.com",
    # Amazon internal ads/tracking
    "amazon-adsystem.com", "axp.amazon-adsystem.com",
    "amazon.dev", "paets.advertising.amazon.dev",
    # Antibot own endpoints (not useful)
    "datadome.co", "perimeterx.net", "px.js",
    "awswaf.com", "token.awswaf.com",
    # CDN rum/pixel endpoints
    "cdn-cgi", "akam/", "akamai",
]

EXCLUDED_EXTENSIONS = {
    ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
    ".woff", ".woff2", ".ttf", ".eot", ".ico", ".mp4", ".mp3",
    ".pdf", ".zip", ".glb", ".gltf",
}

API_INLINE_PATTERNS = [
    r"""fetch\s*\(\s*['"`]([^'"`\s]{10,})['"`]""",
    r"""axios\s*\.\s*(?:get|post|put|delete|patch)\s*\(\s*['"`]([^'"`\s]{10,})['"`]""",
    r"""(?:url|endpoint|apiUrl|baseUrl)\s*[=:]\s*['"`](https?://[^'"`\s]{10,})['"`]""",
]


def _is_excluded(domain: str) -> bool:
    return any(excl in domain for excl in EXCLUDED_DOMAINS)


def _looks_like_api(domain: str) -> bool:
    parts = domain.lower().split(".")
    return parts[0] in {"api", "gateway", "gql", "graphql", "rest", "data", "backend", "service", "services"}


def _extract_from_csp(headers: Any) -> list[str]:
    found = []
    csp_headers = [
        headers.get("content-security-policy", ""),
        headers.get("content-security-policy-report-only", ""),
    ]
    url_pattern = re.compile(r"https?://([^\s;,]+)")
    for csp in csp_headers:
        for match in url_pattern.finditer(csp):
            raw_url = match.group(0).rstrip("/;,")
            domain = urlparse(raw_url).netloc
            if not _is_excluded(domain) and _looks_like_api(domain) and raw_url not in found:
                found.append(raw_url)
    return found


def _extract_from_next_data(html: str) -> list[str]:
    found = []
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        return found
    try:
        data = json.loads(match.group(1))
        raw = json.dumps(data)
        for m in re.finditer(r'"(https?://[^"]{10,})"', raw):
            url = m.group(1)
            domain = urlparse(url).netloc
            if not _is_excluded(domain) and _looks_like_api(domain) and url not in found:
                found.append(url)
    except Exception:
        pass
    return found


def _extract_from_inline_scripts(html: str) -> list[str]:
    found = []
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all("script"):
        if not tag.get("src") and tag.string:
            for pattern in API_INLINE_PATTERNS:
                for match in re.finditer(pattern, tag.string):
                    candidate = match.group(1)
                    if candidate.startswith("http"):
                        domain = urlparse(candidate).netloc
                        if not _is_excluded(domain) and candidate not in found:
                            found.append(candidate)
    return found


async def detect(html: str, response: Any) -> dict:
    try:
        endpoints: list[str] = []

        for ep in _extract_from_csp(response.headers):
            if ep not in endpoints:
                endpoints.append(ep)

        for ep in _extract_from_next_data(html):
            if ep not in endpoints:
                endpoints.append(ep)

        for ep in _extract_from_inline_scripts(html):
            if ep not in endpoints:
                endpoints.append(ep)

        return {"detected": len(endpoints) > 0, "endpoints": endpoints}
    except Exception:
        return None

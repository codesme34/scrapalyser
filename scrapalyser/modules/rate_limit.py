"""Rate limit hints sent by the server: how many requests are allowed, how many
are left, and how long to wait."""

from typing import Any, Optional

# Header name -> field of the result. Covers the common spellings
# (X-RateLimit-*, RateLimit-* from the IETF draft, X-Rate-Limit-*).
HEADERS = {
    "retry-after": "retry_after",
    "x-ratelimit-limit": "limit",
    "x-ratelimit-remaining": "remaining",
    "x-ratelimit-reset": "reset",
    "ratelimit-limit": "limit",
    "ratelimit-remaining": "remaining",
    "ratelimit-reset": "reset",
    "ratelimit-policy": "policy",
    "ratelimit": "policy",
    "x-rate-limit-limit": "limit",
    "x-rate-limit-remaining": "remaining",
    "x-rate-limit-reset": "reset",
}


def detect(headers: Any) -> Optional[dict]:
    try:
        lowered = {k.lower(): str(v) for k, v in headers.items()}
        found = {}
        raw = {}
        for name, field in HEADERS.items():
            if name in lowered:
                raw[name] = lowered[name]
                found.setdefault(field, lowered[name])
        return {
            "detected": bool(found),
            "limit": found.get("limit"),
            "remaining": found.get("remaining"),
            "reset": found.get("reset"),
            "retry_after": found.get("retry_after"),
            "policy": found.get("policy"),
            "headers": raw,
        }
    except Exception:
        return None

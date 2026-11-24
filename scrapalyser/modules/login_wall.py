import re
from typing import Any, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup


# Matched on whole path segments, so "/auth" does not match "/author"
LOGIN_PATH_PATTERN = re.compile(
    r"(?:^|/)(?:login|log-in|signin|sign-in|sign_in|auth|connexion|se-connecter|compte)(?:/|\.|$)",
    re.IGNORECASE,
)

LOGIN_BUTTON_TEXTS = [
    "se connecter", "connexion", "login", "log in", "sign in",
    "entrar", "iniciar sesión", "fazer login",
]

# Longer texts are paragraphs, not login buttons
MAX_BUTTON_TEXT_LENGTH = 40

OAUTH_SCRIPTS = ["accounts.google.com", "connect.facebook.net", "appleid.apple.com"]

# A page holding a password field and little else is a login page
LOGIN_PAGE_MAX_TEXT = 2000

NON_VISIBLE_TAGS = ["script", "style", "noscript", "template"]


def _result(required: bool, login_type: Optional[str], available: bool) -> dict:
    return {"detected": required, "type": login_type, "login_available": available}


def _has_login_entry(soup: BeautifulSoup) -> bool:
    for tag in soup.find_all(["a", "button"]):
        text = tag.get_text(" ", strip=True).lower()
        if text and len(text) <= MAX_BUTTON_TEXT_LENGTH and any(t in text for t in LOGIN_BUTTON_TEXTS):
            return True
    scripts = " ".join(tag.get("src", "") for tag in soup.find_all("script"))
    return any(oauth in scripts for oauth in OAUTH_SCRIPTS)


def _visible_text_length(soup: BeautifulSoup) -> int:
    for tag in soup(NON_VISIBLE_TAGS):
        tag.decompose()
    return len(soup.get_text(" ", strip=True))


async def detect(response: Any, html: str, requested_url: Optional[str] = None) -> dict:
    """
    detected        -> a login is REQUIRED to see the content
    login_available -> the site offers a login (may be optional)
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        has_password = soup.find("input", {"type": "password"}) is not None
        available = has_password or _has_login_entry(soup)

        if getattr(response, "status_code", None) == 401:
            return _result(True, "http_401", True)

        # Redirected to a login page (and the scanned URL was not one already)
        final_path = urlparse(str(response.url)).path
        requested_path = urlparse(requested_url).path if requested_url else ""
        if LOGIN_PATH_PATTERN.search(final_path) and not LOGIN_PATH_PATTERN.search(requested_path):
            return _result(True, "redirect", True)

        # The page itself is essentially a login form
        if has_password and _visible_text_length(soup) < LOGIN_PAGE_MAX_TEXT:
            return _result(True, "form", True)

        return _result(False, None, available)
    except Exception:
        return None

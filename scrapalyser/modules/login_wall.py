from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import Any


LOGIN_PATH_PATTERNS = ["/login", "/signin", "/sign-in", "/auth", "/compte", "/connexion"]

LOGIN_BUTTON_TEXTS = [
    "se connecter", "connexion", "login", "log in", "sign in",
    "entrar", "iniciar sesión", "fazer login",
]

OAUTH_SCRIPTS = ["accounts.google.com", "connect.facebook.net", "appleid.apple.com"]


async def detect(response: Any, html: str) -> dict:
    try:
        parsed = urlparse(str(response.url))
        if any(pattern in parsed.path.lower() for pattern in LOGIN_PATH_PATTERNS):
            return {"detected": True, "type": "redirect"}

        soup = BeautifulSoup(html, "html.parser")

        for form in soup.find_all("form"):
            if form.find("input", {"type": "password"}):
                return {"detected": True, "type": "form"}

        for tag in soup.find_all(["a", "button"]):
            tag_text = tag.get_text(strip=True).lower()
            if any(text in tag_text for text in LOGIN_BUTTON_TEXTS):
                return {"detected": True, "type": "button"}

        scripts = " ".join(tag.get("src", "") for tag in soup.find_all("script"))
        if any(oauth in scripts for oauth in OAUTH_SCRIPTS):
            return {"detected": True, "type": "oauth"}

        return {"detected": False, "type": None}
    except Exception:
        return None

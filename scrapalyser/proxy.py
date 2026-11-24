"""Proxy parsing: accepts the formats proxy providers hand out and converts
them for curl_cffi (a URL) and Playwright (server + username + password)."""

from typing import Optional
from urllib.parse import quote, unquote

SCHEMES = ("http", "https", "socks5", "socks5h", "socks4")

FORMATS_HELP = (
    "accepted formats: scheme://user:pass@host:port, user:pass@host:port, "
    "host:port:user:pass, user:pass:host:port, host:port "
    f"(scheme: {', '.join(SCHEMES)}; http by default)"
)


def _is_port(value: str) -> bool:
    return value.isdigit() and 0 < int(value) < 65536


class Proxy:
    def __init__(self, scheme: str, host: str, port: int,
                 username: Optional[str] = None, password: Optional[str] = None):
        self.scheme = scheme
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    @property
    def server(self) -> str:
        return f"{self.scheme}://{self.host}:{self.port}"

    def for_curl(self) -> str:
        """Full URL for curl_cffi, credentials percent-encoded."""
        if self.username is None:
            return self.server
        auth = quote(self.username, safe="")
        if self.password is not None:
            auth += ":" + quote(self.password, safe="")
        return f"{self.scheme}://{auth}@{self.host}:{self.port}"

    def for_playwright(self) -> dict:
        """Chromium wants the credentials apart from the server."""
        conf = {"server": self.server}
        if self.username is not None:
            conf["username"] = self.username
            conf["password"] = self.password or ""
        return conf

    def hide(self, text: str) -> str:
        """Remove the password from a message (errors may echo the proxy URL)."""
        if not self.password:
            return text
        for secret in {self.password, quote(self.password, safe="")}:
            text = text.replace(secret, "***")
        return text

    def __repr__(self) -> str:
        user = f"{self.username}:***@" if self.username else ""
        return f"Proxy({self.scheme}://{user}{self.host}:{self.port})"


def parse_proxy(value: str) -> Proxy:
    raw = value.strip().strip("'\"")
    if not raw:
        raise ValueError(f"Empty proxy — {FORMATS_HELP}")

    scheme = "http"
    if "://" in raw:
        scheme, raw = raw.split("://", 1)
        scheme = scheme.lower()
        if scheme not in SCHEMES:
            raise ValueError(f"Unsupported proxy scheme {scheme!r} — {FORMATS_HELP}")
    raw = raw.rstrip("/")

    username = password = None
    if "@" in raw:
        # rpartition: the password itself may contain "@"
        auth, _, hostport = raw.rpartition("@")
        username, sep, password = auth.partition(":")
        username, password = unquote(username), (unquote(password) if sep else None)
        host, sep, port = hostport.rpartition(":")
        if not sep or not host or not _is_port(port):
            raise ValueError(f"Invalid proxy {value!r}: missing or wrong port — {FORMATS_HELP}")
    else:
        parts = raw.split(":")
        if len(parts) == 2 and _is_port(parts[1]):
            host, port = parts
        elif len(parts) >= 4 and _is_port(parts[1]):
            # host:port:user:pass (the password may contain ":")
            host, port, username, password = parts[0], parts[1], parts[2], ":".join(parts[3:])
        elif len(parts) == 4 and _is_port(parts[3]):
            # user:pass:host:port
            username, password, host, port = parts
        else:
            raise ValueError(f"Invalid proxy format {value!r} — {FORMATS_HELP}")

    if not host:
        raise ValueError(f"Invalid proxy {value!r}: missing host — {FORMATS_HELP}")
    return Proxy(scheme, host, int(port), username, password)

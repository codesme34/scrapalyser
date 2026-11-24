import asyncio

import pytest


class FakeResponse:
    """Stands in for a curl_cffi response."""

    def __init__(self, status_code=200, text="", headers=None, cookies=None, url="https://example.com/"):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}
        self.cookies = cookies or {}
        self.url = url

    async def aiter_content(self):
        yield self.text.encode()

    async def aclose(self):
        pass


class FakeSession:
    """Answers GET requests from a {url: FakeResponse} map; anything else is a 404."""

    def __init__(self, pages):
        self.pages = pages
        self.requested = []

    async def get(self, url, timeout=None, stream=False):
        self.requested.append(url)
        return self.pages.get(url, FakeResponse(404, "not found"))


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def fake_response():
    return FakeResponse


@pytest.fixture
def fake_session():
    return FakeSession

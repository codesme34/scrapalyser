import pytest

from scrapalyser.proxy import parse_proxy

EXPECTED = "http://alice:s3cret@gw.provider.com:823"


@pytest.mark.parametrize("value", [
    "http://alice:s3cret@gw.provider.com:823",
    "alice:s3cret@gw.provider.com:823",
    "gw.provider.com:823:alice:s3cret",
    "alice:s3cret:gw.provider.com:823",
    '"http://alice:s3cret@gw.provider.com:823/"',  # quotes and trailing slash from a .env file
    "  http://alice:s3cret@gw.provider.com:823  ",
])
def test_accepted_formats(value):
    p = parse_proxy(value)
    assert p.for_curl() == EXPECTED
    assert p.for_playwright() == {"server": "http://gw.provider.com:823", "username": "alice", "password": "s3cret"}


def test_no_auth():
    p = parse_proxy("1.2.3.4:8080")
    assert p.for_curl() == "http://1.2.3.4:8080"
    assert p.for_playwright() == {"server": "http://1.2.3.4:8080"}


def test_special_characters_in_password():
    p = parse_proxy("http://alice:p@ss:w0rd@gw.provider.com:823")
    assert p.password == "p@ss:w0rd"
    assert p.for_curl() == "http://alice:p%40ss%3Aw0rd@gw.provider.com:823"


def test_socks5():
    assert parse_proxy("socks5://a:b@h.com:824").for_curl() == "socks5://a:b@h.com:824"


@pytest.mark.parametrize("value", ["", "ftp://h:1", "gw.provider.com", "alice:pw@host", "a:b:c", "host:99999"])
def test_invalid_formats(value):
    with pytest.raises(ValueError, match="accepted formats"):
        parse_proxy(value)


def test_password_is_never_shown():
    p = parse_proxy(EXPECTED)
    assert "s3cret" not in repr(p)
    assert p.hide("CONNECT failed for http://alice:s3cret@gw") == "CONNECT failed for http://alice:***@gw"

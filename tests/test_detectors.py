"""Antibot, technology, JS, embedded data and rate limit detectors."""

import pytest

from conftest import FakeResponse, run
from scrapalyser.modules import antibot, embedded_data, js_check, rate_limit, technology


def detect_antibot(headers=None, cookies=None, html=""):
    return run(antibot.detect(FakeResponse(headers=headers, cookies=cookies), html))


# --- antibot -------------------------------------------------------------------------

@pytest.mark.parametrize("kwargs, expected", [
    ({"headers": {"cf-ray": "x"}}, "Cloudflare"),
    ({"html": '<script src="https://challenges.cloudflare.com/turnstile/v0/api.js"></script>'}, "Cloudflare Turnstile"),
    ({"cookies": {"datadome": "x"}}, "DataDome"),
    ({"cookies": {"_px3": "x"}}, "PerimeterX"),
    ({"headers": {"akamai-grn": "0.54c8c217"}}, "Akamai"),
    ({"cookies": {"_abck": "x"}}, "Akamai"),
    ({"headers": {"x-kpsdk-ct": "x"}}, "Kasada"),
    ({"cookies": {"KP_UIDz": "x"}}, "Kasada"),
    ({"cookies": {"incap_ses_123_456": "x"}}, "Imperva"),
    ({"headers": {"x-sucuri-id": "1"}}, "Sucuri"),
    ({"cookies": {"_fs_ch_st_FSBmUei20MqUiJb9": "x"}}, "Fastly"),
    ({"headers": {"x-amz-cf-id": "x"}}, "AWS WAF / CloudFront"),
    ({"html": '<script src="/recaptcha/api.js"></script>'}, "reCAPTCHA"),   # relative path (Google demo)
    ({"html": '<script src="https://js.hcaptcha.com/1/api.js"></script>'}, "hCaptcha"),
])
def test_antibot_signatures(kwargs, expected):
    result = detect_antibot(**kwargs)
    assert result["detected"] and expected in result["all"]


def test_turnstile_only_with_its_script():
    # cf-ray / __cf_bm are on every Cloudflare site: that is not Turnstile
    result = detect_antibot(headers={"cf-ray": "x"}, cookies={"__cf_bm": "y"})
    assert result["all"] == ["Cloudflare"]


def test_all_antibots_are_listed():
    result = detect_antibot(headers={"cf-ray": "x"}, cookies={"_px3": "y"})
    assert result["all"] == ["Cloudflare", "PerimeterX"]


def test_no_antibot():
    assert detect_antibot(html="<p>hello</p>") == {"detected": False, "name": None, "all": []}


# --- technology ----------------------------------------------------------------------

def detect_tech(html, url="https://monsite.fr/", headers=None):
    return run(technology.detect(FakeResponse(headers=headers, url=url), html))["type"]


def test_google_results_are_not_wordpress():
    html = '<a href="https://blog.fr/wp-content/x.jpg">r</a><img src="https://blog.fr/wp-content/uploads/a.png">'
    assert detect_tech(html, url="https://www.google.com/search?q=a") == "Static HTML"


@pytest.mark.parametrize("html", [
    '<link rel="stylesheet" href="/wp-content/themes/t/style.css">',
    '<script src="https://cdn.monsite.fr/wp-includes/js/jquery.js"></script>',
    '<meta name="generator" content="WordPress 6.5">',
])
def test_wordpress(html):
    assert detect_tech(html) == "WordPress"


def test_nextjs():
    assert detect_tech('<script id="__NEXT_DATA__" type="application/json">{}</script>') == "Next.js"


# --- js_check ------------------------------------------------------------------------

def js_required(html):
    return run(js_check.detect("https://x", html))["js_required"]


def test_spa_shell_needs_js():
    assert js_required('<div id="root"></div>' + "<script src='a.js'></script>" * 4)


def test_server_rendered_page_does_not_need_js():
    text = "<p>" + "Annonce Audi A3 très bon état. " * 40 + "</p>"
    assert not js_required(f'<div id="__next">{text}</div><script id="__NEXT_DATA__">{{}}</script>')


def test_inline_json_is_not_visible_text():
    big_json = '{"a": "' + "x" * 5000 + '"}'
    html = f'<div id="root"></div><script>{big_json}</script>' + "<script src='a.js'></script>" * 4
    assert js_required(html)


# --- embedded data -------------------------------------------------------------------

def test_embedded_next_data_and_json_ld():
    html = ('<script type="application/ld+json">{"@type": "Product", "name": "Shoe"}</script>'
            '<script id="__NEXT_DATA__" type="application/json">{"props": {}}</script>')
    result = embedded_data.detect(html)
    types = {s["type"] for s in result["sources"]}
    assert result["detected"]
    assert "Next.js (__NEXT_DATA__)" in types and "JSON-LD (schema.org)" in types
    ld = next(s for s in result["sources"] if s["type"].startswith("JSON-LD"))
    assert ld["schema_types"] == ["Product"]


def test_embedded_window_state_and_graph_json_ld():
    html = ('<script>window.__INITIAL_STATE__ = {"items": []};</script>'
            '<script type="application/ld+json">{"@graph": [{"@type": "WebSite"}, {"@type": ["Organization"]}]}</script>')
    result = embedded_data.detect(html)
    selectors = {s["selector"] for s in result["sources"]}
    assert "window.__INITIAL_STATE__" in selectors
    ld = next(s for s in result["sources"] if s["type"].startswith("JSON-LD"))
    assert ld["schema_types"] == ["WebSite", "Organization"]


def test_next_app_router_chunks_are_added_up():
    html = '<script>self.__next_f.push([1,"aaaa"])</script><script>self.__next_f.push([1,"bbbb"])</script>'
    sources = embedded_data.detect(html)["sources"]
    assert len(sources) == 1 and sources[0]["selector"] == "self.__next_f"
    assert sources[0]["size"] == sum(len(f'self.__next_f.push([1,"{c}"])') for c in ("aaaa", "bbbb"))


def test_no_embedded_data():
    assert embedded_data.detect("<p>hello</p><script>console.log(1)</script>") == {"detected": False, "sources": []}


def test_broken_json_ld_does_not_crash():
    result = embedded_data.detect('<script type="application/ld+json">{not json</script>')
    assert result["detected"] and result["sources"][0]["schema_types"] == []


# --- rate limit ----------------------------------------------------------------------

def test_rate_limit_headers():
    result = rate_limit.detect({"X-RateLimit-Limit": "60", "X-RateLimit-Remaining": "59",
                                "X-RateLimit-Reset": "1795516826", "Retry-After": "30"})
    assert result["detected"]
    assert (result["limit"], result["remaining"], result["reset"], result["retry_after"]) == ("60", "59", "1795516826", "30")


def test_ietf_ratelimit_headers():
    result = rate_limit.detect({"RateLimit-Limit": "100", "RateLimit-Policy": "100;w=60"})
    assert result["limit"] == "100" and result["policy"] == "100;w=60"


def test_no_rate_limit():
    assert not rate_limit.detect({"content-type": "text/html"})["detected"]

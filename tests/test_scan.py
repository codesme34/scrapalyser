"""scan(), scan_many(), the auto engine fallback, the text report and the CLI,
with the engines replaced by fakes (no network, no browser)."""

import json
import time

import pytest

import scrapalyser
from scrapalyser import cli, scanner
from scrapalyser.i18n.labels import LABELS
from scrapalyser.output.txt_output import render

BLOCKED = "blocked by antibot"


def report(engine, blocked=False, url="https://x.test"):
    base = {"url": url, "scanned_at": "2026-01-01T00:00:00Z", "engine": engine,
            "antibot": {"detected": True, "name": "Cloudflare", "all": ["Cloudflare"]},
            "rate_limit": {"detected": False}}
    if blocked:
        return {**base, "status_code": 403,
                "blocking": {"reason": "ip_banned", "code": "1006", "ray_id": "r-MRS"},
                **{k: BLOCKED for k in ("technology", "js_required", "api", "embedded_data",
                                        "robots_txt", "sitemap", "login_wall")}}
    return {**base, "status_code": 200, "blocking": None, "technology": {"type": "Next.js"},
            "js_required": False, "api": {"detected": False, "endpoints": []},
            "embedded_data": {"detected": True, "sources": [
                {"type": "Next.js (__NEXT_DATA__)", "selector": "script#__NEXT_DATA__", "size": 4096}]},
            "robots_txt": {"found": True, "url": "https://x.test/robots.txt", "allowed": True, "crawl_delay": 2.0},
            "sitemap": {"found": True, "url": "https://x.test/a.xml", "urls": ["https://x.test/a.xml"],
                        "declared_in_robots": 1},
            "login_wall": {"detected": False, "type": None, "login_available": False}}


@pytest.fixture
def engines(monkeypatch):
    """Configure which fake engine is blocked; records the calls."""
    state = {"curl_blocked": False, "pw_blocked": False, "pw_error": None, "calls": []}

    async def fake_curl(url, proxy=None, timeout=30):
        state["calls"].append(("curl", url, timeout))
        return report("curl", state["curl_blocked"], url)

    async def fake_pw(url, headless, screenshot, proxy=None, timeout=30):
        state["calls"].append(("playwright", url, timeout))
        if state["pw_error"]:
            raise state["pw_error"]
        return report("playwright", state["pw_blocked"], url)

    monkeypatch.setattr(scanner, "_scan_curl", fake_curl)
    monkeypatch.setattr(scanner, "_scan_playwright", fake_pw)
    return state


# --- auto engine ---------------------------------------------------------------------

def test_auto_curl_passes_playwright_not_launched(engines):
    r = scrapalyser.scan("https://x.test")
    assert r["engine"] == "curl" and [c[0] for c in engines["calls"]] == ["curl"]


def test_auto_falls_back_to_playwright(engines):
    engines["curl_blocked"] = True
    r = scrapalyser.scan("https://x.test")
    assert r["engine"] == "playwright" and r["blocking"] is None
    assert [a["passed"] for a in r["attempts"]] == [False, True]


def test_auto_both_blocked(engines):
    engines["curl_blocked"] = engines["pw_blocked"] = True
    r = scrapalyser.scan("https://x.test")
    assert r["blocking"]["reason"] == "ip_banned"
    assert [a["engine"] for a in r["attempts"]] == ["curl", "playwright"]


def test_auto_playwright_missing_keeps_curl_result(engines):
    engines["curl_blocked"] = True
    engines["pw_error"] = ImportError("No module named 'playwright'")
    r = scrapalyser.scan("https://x.test")
    assert r["engine"] == "curl"
    assert r["attempts"][1]["error"] == "No module named 'playwright'"


def test_proxy_password_never_in_report(engines):
    r = scrapalyser.scan("https://x.test", proxy="http://alice:s3cret@gw.provider.com:823")
    assert r["proxy"] == "http://gw.provider.com:823"
    assert "s3cret" not in json.dumps(r) and "alice" not in json.dumps(r)


def test_timeout_is_passed_to_the_engines(engines):
    engines["curl_blocked"] = True
    scrapalyser.scan("https://x.test", timeout=60)
    assert {c[2] for c in engines["calls"]} == {60.0}


@pytest.mark.parametrize("kwargs", [{"engine": "foo"}, {"timeout": 0}, {"timeout": -1}, {"timeout": "30"},
                                    {"proxy": "nimporte"}])
def test_bad_arguments(kwargs):
    with pytest.raises(ValueError):
        scrapalyser.scan("https://x.test", **kwargs)


# --- scan_many -----------------------------------------------------------------------

def test_scan_many_keeps_order_and_errors(monkeypatch):
    delays = {"https://a.test": 0.3, "https://b.test": 0.05, "https://c.test": 0.1}

    def fake_build(url, engine, headless, screenshot, proxy, timeout=30):
        time.sleep(delays[url])
        if url == "https://c.test":
            raise RuntimeError("boom")
        return report("curl", url=url)

    monkeypatch.setattr(scanner, "_build_report", fake_build)
    start = time.time()
    results = scrapalyser.scan_many(list(delays), workers=3)
    assert time.time() - start < 0.45  # in parallel, not 0.45s one after the other
    assert [r["url"] for r in results] == list(delays)
    assert results[2] == {"url": "https://c.test", "error": "RuntimeError: boom"}


def test_scan_many_save_dir(engines, tmp_path):
    scrapalyser.scan_many(["https://a.test/p", "https://b.test"], workers=2, save_dir=str(tmp_path))
    assert sorted(p.name for p in tmp_path.iterdir()) == ["001_a.test.json", "002_b.test.json"]


@pytest.mark.parametrize("workers", [0, -2, 2.5, "4"])
def test_scan_many_bad_workers(workers):
    with pytest.raises(ValueError, match="workers"):
        scrapalyser.scan_many(["https://x.test"], workers=workers)


def test_scan_many_empty():
    assert scrapalyser.scan_many([]) == []


# --- text report ---------------------------------------------------------------------

def test_all_languages_have_the_same_labels():
    keys = set(LABELS["en"])
    for lang, labels in LABELS.items():
        assert set(labels) == keys, lang


@pytest.mark.parametrize("lang", list(LABELS))
@pytest.mark.parametrize("blocked", [False, True])
def test_render_every_language(lang, blocked):
    r = report("curl", blocked)
    r["attempts"] = [{"engine": "curl", "status_code": r["status_code"], "passed": not blocked}]
    text = render(r, lang)
    assert LABELS[lang]["title"] in text
    if blocked:
        assert LABELS[lang]["reason_ip_banned"] in text and LABELS[lang]["blocked"] in text
    else:
        assert "script#__NEXT_DATA__" in text and "https://x.test/a.xml" in text


def test_every_block_reason_has_a_label():
    for reason in ("ip_banned", "country_blocked", "browser_signature", "firewall_rule",
                   "rate_limited", "js_challenge", "captcha", "access_denied"):
        r = report("curl", blocked=True)
        r["blocking"]["reason"] = reason
        for lang in LABELS:
            render(r, lang)


def test_txt_report_printed_once(engines, capsys):
    scrapalyser.scan("https://x.test", output="txt")
    assert capsys.readouterr().out.count("SCRAPALYSER REPORT") == 1


# --- CLI -----------------------------------------------------------------------------

def test_cli_json(engines, capsys):
    assert cli.main(["https://x.test", "--json", "--engine", "curl"]) == 0
    assert json.loads(capsys.readouterr().out)["engine"] == "curl"


def test_cli_several_urls(engines, capsys):
    assert cli.main(["https://a.test", "https://b.test", "--json", "--workers", "2"]) == 0
    assert [r["url"] for r in json.loads(capsys.readouterr().out)] == ["https://a.test", "https://b.test"]


def test_cli_proxy_from_environment(engines, monkeypatch, capsys):
    monkeypatch.setenv("SCRAPALYSER_PROXY", "alice:s3cret@gw.provider.com:823")
    cli.main(["https://x.test", "--json"])
    assert json.loads(capsys.readouterr().out)["proxy"] == "http://gw.provider.com:823"


def test_cli_bad_proxy(capsys):
    assert cli.main(["https://x.test", "--proxy", "nimporte"]) == 2
    assert "accepted formats" in capsys.readouterr().err


# --- scan() with a list of URLs and workers ------------------------------------------

def test_scan_accepts_a_list_with_workers(engines):
    results = scrapalyser.scan(["https://a.test", "https://b.test", "https://c.test"], workers=3)
    assert [r["url"] for r in results] == ["https://a.test", "https://b.test", "https://c.test"]


def test_scan_list_is_the_same_as_scan_many(engines):
    urls = ("https://a.test", "https://b.test")  # any iterable works
    assert [r["url"] for r in scrapalyser.scan(urls)] == [r["url"] for r in scrapalyser.scan_many(urls)]


def test_scan_single_url_still_returns_one_report(engines):
    assert isinstance(scrapalyser.scan("https://a.test", workers=8), dict)


def test_scan_list_save_dir(engines, tmp_path):
    scrapalyser.scan(["https://a.test", "https://b.test"], save_dir=str(tmp_path))
    assert sorted(p.name for p in tmp_path.iterdir()) == ["001_a.test.json", "002_b.test.json"]


@pytest.mark.parametrize("kwargs", [{"save": "r.json"}, {"screenshot": "s.png"}])
def test_scan_list_rejects_single_file_options(kwargs):
    with pytest.raises(ValueError, match="save_dir"):
        scrapalyser.scan(["https://a.test", "https://b.test"], **kwargs)


@pytest.mark.parametrize("workers", [0, True, 2.5])
def test_scan_bad_workers(workers):
    with pytest.raises(ValueError, match="workers"):
        scrapalyser.scan(["https://a.test"], workers=workers)

"""robots.txt rules and sitemap discovery, without network."""

from conftest import FakeResponse, FakeSession, run
from scrapalyser.modules import robots

BASE = "https://shop.test"
SITEMAP_XML = '<?xml version="1.0"?><urlset><url><loc>https://shop.test/a</loc></url></urlset>'


def scan(pages, url=f"{BASE}/products/1"):
    return run(robots.detect(url, FakeSession(pages)))


def test_rules_and_all_declared_sitemaps():
    robots_txt = ("User-agent: *\nDisallow: /account/\nCrawl-delay: 5\n"
                  f"Sitemap: {BASE}/sitemap-products.xml\nSitemap: {BASE}/sitemap-pages.xml\n"
                  f"Sitemap: {BASE}/sitemap-dead.xml\n")
    result = scan({
        f"{BASE}/robots.txt": FakeResponse(200, robots_txt),
        f"{BASE}/sitemap-products.xml": FakeResponse(200, SITEMAP_XML, {"content-type": "application/xml"}),
        f"{BASE}/sitemap-pages.xml": FakeResponse(200, SITEMAP_XML, {"content-type": "text/plain"}),
    })
    assert result["robots_txt"] == {"found": True, "url": f"{BASE}/robots.txt", "allowed": True, "crawl_delay": 5.0}
    # the dead sitemap (404) is not reported as working
    assert result["sitemap"]["urls"] == [f"{BASE}/sitemap-products.xml", f"{BASE}/sitemap-pages.xml"]
    assert result["sitemap"]["url"] == f"{BASE}/sitemap-products.xml"
    assert result["sitemap"]["declared_in_robots"] == 3


def test_disallowed_page():
    result = scan({f"{BASE}/robots.txt": FakeResponse(200, "User-agent: *\nDisallow: /products/\n")})
    assert result["robots_txt"]["allowed"] is False


def test_dead_declared_sitemap_falls_back_to_usual_paths():
    result = scan({
        f"{BASE}/robots.txt": FakeResponse(200, f"User-agent: *\nSitemap: {BASE}/gone.xml\n"),
        f"{BASE}/sitemap.xml": FakeResponse(200, SITEMAP_XML),
    })
    assert result["sitemap"]["urls"] == [f"{BASE}/sitemap.xml"]


def test_html_page_on_sitemap_path_is_not_a_sitemap():
    # some sites answer 200 with their home page for any URL
    result = scan({f"{BASE}/sitemap.xml": FakeResponse(200, "<html><body>Home</body></html>", {"content-type": "text/html"})})
    assert result["sitemap"]["found"] is False


def test_nothing_found():
    result = scan({})
    assert result["robots_txt"]["found"] is False
    assert result["sitemap"] == {"found": False, "url": None, "urls": [], "declared_in_robots": 0}

import os

import scrapalyser

# Simple scan (returns dict): curl_cffi first, Playwright if blocked
report = scrapalyser.scan("https://example.com")
print(report)

# Text report (English by default, lang="fr", "es" or "br" for other languages), saved to a file
scrapalyser.scan(
    url="https://example.com",
    output="txt",
    save="report.txt",
)

# With a proxy, format: http://USER:PASSWORD@HOST:PORT (here read from the PROXY env variable)
if os.environ.get("PROXY"):
    report = scrapalyser.scan("https://example.com", proxy=os.environ["PROXY"])
    print(report["attempts"])

# Force one engine, hidden browser, screenshot
report = scrapalyser.scan(
    url="https://example.com",
    engine="playwright",
    headless=True,
    screenshot="shot.png",
)

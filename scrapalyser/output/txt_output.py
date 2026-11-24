from typing import Any
from ..i18n.labels import LABELS
from ..modules.robots import MAX_SITEMAPS_CHECKED

SEP = "═" * 43
BLOCKED = "blocked by antibot"
ENGINE_NAMES = {"curl": "curl_cffi", "playwright": "Playwright"}


def _blocked(val: Any) -> bool:
    return val == BLOCKED


def render(report: dict[str, Any], lang: str = "en") -> str:
    L = LABELS.get(lang, LABELS["en"])
    lines: list[str] = []

    lines.append(SEP)
    lines.append(f"        {L['title']}")
    lines.append(f"        {report.get('url', '')}")
    lines.append(f"        {L['scanned_at']} : {report.get('scanned_at', '')}")
    lines.append(f"        Status : {report.get('status_code', '?')}")
    if report.get("proxy"):
        lines.append(f"        Proxy : {report['proxy']}")
    lines.append(SEP)

    # Engines tried, in order
    attempts = report.get("attempts")
    if attempts:
        lines.append(f"\n[{L['engines']}]")
        for a in attempts:
            name = ENGINE_NAMES.get(a.get("engine"), a.get("engine"))
            if a.get("passed"):
                lines.append(f"  ✅  {name} : {L['engine_passed']} ({a.get('status_code')})")
            elif a.get("error"):
                lines.append(f"  ❌  {name} : {L['engine_error']} ({a['error']})")
            else:
                lines.append(f"  ❌  {name} : {L['engine_blocked']} ({a.get('status_code')})")
        winner = next((a for a in attempts if a.get("passed")), None)
        if winner:
            name = ENGINE_NAMES.get(winner["engine"], winner["engine"])
            lines.append(f"  👉  {L['engine_use']} : {name}")
        else:
            lines.append(f"  👉  {L['engine_none']}")

    # Anti-bot
    lines.append(f"\n[{L['antibot']}]")
    antibot = report.get("antibot")
    if antibot and antibot.get("detected"):
        names = antibot.get("all") or [antibot["name"]]
        lines.append(f"  ⚠️  {L['antibot_detected']} : {', '.join(names)}")
    else:
        lines.append(f"  ✅  {L['antibot_none']}")

    # Blocking diagnosis (only when the site blocked the scan)
    blocking = report.get("blocking")
    if isinstance(blocking, dict):
        reason = blocking.get("reason", "access_denied")
        lines.append(f"\n[{L['blocking']}]")
        lines.append(f"  ⛔  {L['reason_' + reason]}")
        if blocking.get("code"):
            lines.append(f"  •  {L['block_code']} : {blocking['code']}")
        if blocking.get("ray_id"):
            lines.append(f"  •  {L['ray_id']} : {blocking['ray_id']}")
        lines.append(f"  💡  {L['advice']} : {L['advice_' + reason]}")

    # Technology
    lines.append(f"\n[{L['technology']}]")
    tech = report.get("technology")
    if _blocked(tech):
        lines.append(f"  ⚠️  {L['blocked']}")
    elif isinstance(tech, dict):
        lines.append(f"  🖥️  Type : {tech.get('type', '?')}")

    # JavaScript
    lines.append(f"\n[{L['js']}]")
    js = report.get("js_required")
    if _blocked(js):
        lines.append(f"  ⚠️  {L['blocked']}")
    elif js:
        lines.append(f"  ⚠️  {L['js_required']}")
    else:
        lines.append(f"  ✅  {L['js_not_required']}")

    # API
    lines.append(f"\n[{L['api']}]")
    api = report.get("api")
    if _blocked(api):
        lines.append(f"  ⚠️  {L['blocked']}")
    elif isinstance(api, dict) and api.get("detected") and api.get("endpoints"):
        for ep in api["endpoints"]:
            lines.append(f"  ✅  {ep}")
    else:
        lines.append(f"  —  {L['api_none']}")

    # Embedded data
    lines.append(f"\n[{L['embedded']}]")
    embedded = report.get("embedded_data")
    if _blocked(embedded):
        lines.append(f"  ⚠️  {L['blocked']}")
    elif isinstance(embedded, dict) and embedded.get("detected"):
        lines.append(f"  💡  {L['embedded_hint']}")
        for src in embedded.get("sources", []):
            size_kb = max(1, round(src.get("size", 0) / 1024))
            line = f"  ✅  {src['type']} → {src['selector']} (~{size_kb} KB)"
            if src.get("schema_types"):
                line += f" : {', '.join(src['schema_types'][:8])}"
            lines.append(line)
    elif isinstance(embedded, dict):
        lines.append(f"  —  {L['embedded_none']}")

    # Robots.txt
    lines.append(f"\n[{L['robots']}]")
    robots = report.get("robots_txt")
    if _blocked(robots):
        lines.append(f"  ⚠️  {L['blocked']}")
    elif isinstance(robots, dict) and robots.get("found"):
        lines.append(f"  ✅  {robots.get('url', '')}")
        if robots.get("allowed") is True:
            lines.append(f"  ✅  {L['robots_allowed']}")
        elif robots.get("allowed") is False:
            lines.append(f"  ⚠️  {L['robots_disallowed']}")
        if robots.get("crawl_delay") is not None:
            delay = robots["crawl_delay"]
            lines.append(f"  ⏱️  {L['crawl_delay'].format(n=int(delay) if delay == int(delay) else delay)}")
    else:
        lines.append(f"  —  {L['not_found']}")

    # Sitemap
    lines.append(f"\n[{L['sitemap']}]")
    sitemap = report.get("sitemap")
    if _blocked(sitemap):
        lines.append(f"  ⚠️  {L['blocked']}")
    elif isinstance(sitemap, dict) and sitemap.get("found"):
        for sitemap_url in sitemap.get("urls") or [sitemap.get("url", "")]:
            lines.append(f"  ✅  {sitemap_url}")
        declared = sitemap.get("declared_in_robots") or 0
        if declared > len(sitemap.get("urls") or []):
            lines.append(f"  •  {L['sitemaps_declared'].format(n=declared, m=min(declared, MAX_SITEMAPS_CHECKED))}")
    else:
        lines.append(f"  —  {L['not_found']}")

    # Rate limit
    lines.append(f"\n[{L['rate_limit']}]")
    rate = report.get("rate_limit")
    if isinstance(rate, dict) and rate.get("detected"):
        for key, label in (("limit", "rate_limit_value"), ("remaining", "rate_remaining"),
                           ("reset", "rate_reset"), ("retry_after", "rate_retry_after")):
            if rate.get(key) is not None:
                lines.append(f"  ⏱️  {L[label]} : {rate[key]}")
        if rate.get("policy"):
            lines.append(f"  •  Policy : {rate['policy']}")
    else:
        lines.append(f"  —  {L['rate_none']}")

    # Login wall
    lines.append(f"\n[{L['login_wall']}]")
    login = report.get("login_wall")
    if _blocked(login):
        lines.append(f"  ⚠️  {L['blocked']}")
    elif isinstance(login, dict) and login.get("detected"):
        lines.append(f"  ⚠️  {L['login_detected']} ({login.get('type', '')})")
    elif isinstance(login, dict) and login.get("login_available"):
        lines.append(f"  ✅  {L['login_optional']}")
    else:
        lines.append(f"  ✅  {L['login_none']}")

    lines.append(f"\n{SEP}")
    return "\n".join(lines)


def save(report: dict[str, Any], path: str, lang: str = "en") -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(render(report, lang))

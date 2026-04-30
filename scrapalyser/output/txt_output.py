from typing import Any
from ..i18n.labels import LABELS

SEP = "═" * 43
BLOCKED = "blocked by antibot"


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
    lines.append(SEP)

    # Anti-bot
    lines.append(f"\n[{L['antibot']}]")
    antibot = report.get("antibot")
    if antibot and antibot.get("detected"):
        lines.append(f"  ⚠️  {L['antibot_detected']} : {antibot['name']}")
    else:
        lines.append(f"  ✅  {L['antibot_none']}")

    # Technology
    lines.append(f"\n[{L['technology']}]")
    tech = report.get("technology")
    if _blocked(tech):
        lines.append(f"  ⚠️  {BLOCKED}")
    elif isinstance(tech, dict):
        lines.append(f"  🖥️  Type : {tech.get('type', '?')}")

    # JavaScript
    lines.append(f"\n[{L['js']}]")
    js = report.get("js_required")
    if _blocked(js):
        lines.append(f"  ⚠️  {BLOCKED}")
    elif js:
        lines.append(f"  ⚠️  {L['js_required']}")
    else:
        lines.append(f"  ✅  {L['js_not_required']}")

    # API
    lines.append(f"\n[{L['api']}]")
    api = report.get("api")
    if _blocked(api):
        lines.append(f"  ⚠️  {BLOCKED}")
    elif isinstance(api, dict) and api.get("detected") and api.get("endpoints"):
        for ep in api["endpoints"]:
            lines.append(f"  ✅  {ep}")
    else:
        lines.append(f"  —  {L['api_none']}")

    # Robots.txt
    lines.append(f"\n[{L['robots']}]")
    robots = report.get("robots_txt")
    if _blocked(robots):
        lines.append(f"  ⚠️  {BLOCKED}")
    elif isinstance(robots, dict) and robots.get("found"):
        lines.append(f"  ✅  {robots.get('url', '')}")
    else:
        lines.append(f"  —  {L['not_found']}")

    # Sitemap
    lines.append(f"\n[{L['sitemap']}]")
    sitemap = report.get("sitemap")
    if _blocked(sitemap):
        lines.append(f"  ⚠️  {BLOCKED}")
    elif isinstance(sitemap, dict) and sitemap.get("found"):
        lines.append(f"  ✅  {sitemap.get('url', '')}")
    else:
        lines.append(f"  —  {L['not_found']}")

    # Login wall
    lines.append(f"\n[{L['login_wall']}]")
    login = report.get("login_wall")
    if _blocked(login):
        lines.append(f"  ⚠️  {BLOCKED}")
    elif isinstance(login, dict) and login.get("detected"):
        lines.append(f"  ⚠️  {L['login_detected']} ({login.get('type', '')})")
    else:
        lines.append(f"  ✅  {L['login_none']}")

    lines.append(f"\n{SEP}")
    return "\n".join(lines)


def save(report: dict[str, Any], path: str, lang: str = "en") -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(render(report, lang))

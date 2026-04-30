import json
from typing import Any


def render(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2)


def save(report: dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(render(report))

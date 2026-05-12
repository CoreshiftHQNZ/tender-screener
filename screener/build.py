"""Render the static screener HTML.

Reads data/scored.json, renders screener/templates/index.html.j2 with
the data embedded as a JS constant, writes dist/index.html.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .dates import NZ

TEMPLATE_DIR = Path("screener/templates")
SCORED_PATH = Path("data/scored.json")
OUT_PATH = Path("dist/index.html")


def main() -> int:
    scored = json.loads(SCORED_PATH.read_text())

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    tpl = env.get_template("index.html.j2")

    now = datetime.now(NZ)
    # Escape `<` so titles containing "</script" can't break out of the script tag.
    items_json = json.dumps(scored["items"], ensure_ascii=False).replace("<", "\\u003c")
    html = tpl.render(
        items_json=items_json,
        generated_at=scored.get("generatedAt", now.isoformat(timespec="seconds")),
        generated_at_display=now.strftime("%a %d %b %Y, %-I:%M %p NZ"),
        item_count=len(scored["items"]),
        new_count=sum(1 for it in scored["items"] if it.get("isNew")),
    )
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html)
    print(f"wrote {OUT_PATH} ({len(html):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

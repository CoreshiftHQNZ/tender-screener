"""Pull current NZ GETS tenders via the Apify actor.

Reads APIFY_TOKEN from env (or .env via simple parsing). Writes the raw
dataset to data/raw.json. Run via `python -m screener.fetch`.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

ACTOR = "fortuitous_pirate~nz-gets-scraper"
ENDPOINT = f"https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items"
OUT_PATH = Path("data/raw.json")
META_PATH = Path("data/raw_meta.json")


def _load_env() -> None:
    """Tiny .env loader so we don't take a dep on python-dotenv."""
    env_path = Path(".env")
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def fetch(token: str, limit: int = 500) -> list[dict]:
    payload = {"searchType": "current", "limit": limit}
    with httpx.Client(timeout=180.0) as client:
        r = client.post(ENDPOINT, params={"token": token}, json=payload)
        r.raise_for_status()
        return r.json()


def main() -> int:
    _load_env()
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        print("error: APIFY_TOKEN not set (env or .env)", file=sys.stderr)
        return 1
    data = fetch(token)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    META_PATH.write_text(json.dumps({
        "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(data),
    }, indent=2))
    print(f"wrote {len(data)} items to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

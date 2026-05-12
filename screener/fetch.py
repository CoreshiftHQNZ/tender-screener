"""Scrape currently-open NZ GETS tenders directly from the public listing.

The GETS portal paginates 25 results per page. We fetch page 1, parse the
"X - Y of Z" indicator to discover the total, then fetch the remaining
pages. No API key required. Run via `python -m screener.fetch`.

We bailed on the Apify actors that the brief originally specified —
both available actors (fortuitous_pirate/nz-gets-scraper and
helixdatalabs/nz-gets-tenders-api) returned only the first page of
results regardless of the requested limit, so the screener was missing
~92% of currently-open tenders.
"""

from __future__ import annotations

import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup, Tag

BASE = "https://www.gets.govt.nz"
INDEX_URL = f"{BASE}/ExternalIndex.htm"
PAGE_SIZE = 25
COUNT_RE = re.compile(r"(\d+)\s*-\s*(\d+)\s*of\s*(\d+)")

OUT_PATH = Path("data/raw.json")
META_PATH = Path("data/raw_meta.json")


def _parse_total(html: str) -> int | None:
    m = COUNT_RE.search(html)
    return int(m.group(3)) if m else None


def _parse_rows(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict] = []
    for tr in soup.select('tr[id^="tender-"]'):
        rfx_id = tr["id"].removeprefix("tender-")
        tds = tr.find_all("td")
        if len(tds) < 6:
            continue

        # Type cell has an abbr with the full name as title="..." and short text inside
        type_cell = tds[3]
        abbr = type_cell.find("abbr")
        if abbr:
            type_full = abbr.get("title", "").strip()
            type_code = abbr.get_text(strip=True)
        else:
            type_full = type_cell.get_text(strip=True)
            type_code = type_full

        # URL — listing uses agency-prefixed relative paths like LINZ/External...
        link = type_cell.find("a") or tds[0].find("a")
        href = link["href"] if link and link.has_attr("href") else f"/ExternalTenderDetails.htm?id={rfx_id}"
        url = href if href.startswith("http") else f"{BASE}/{href.lstrip('/')}"

        rows.append({
            "type": "tender",
            "rfxId": rfx_id,
            "referenceNumber": tds[1].get_text(strip=True),
            "title": tds[2].get_text(strip=True),
            "tenderType": type_full,
            "tenderTypeCode": type_code,
            "closeDate": tds[4].get_text(strip=True),
            "organization": tds[5].get_text(strip=True),
            "status": "open",
            "url": url,
            "contractValue": 0,
            "scrapedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": "NZ GETS",
        })
    return rows


def fetch_all() -> list[dict]:
    headers = {
        "User-Agent": "coreshift-tender-screener/0.1 (+https://github.com/CoreshiftHQNZ/tender-screener)"
    }
    with httpx.Client(timeout=60.0, headers=headers, follow_redirects=True) as client:
        # Page 1: also tells us the total count
        r = client.get(INDEX_URL, params={"page": 1, "orderBy": "date"})
        r.raise_for_status()
        first_html = r.text
        total = _parse_total(first_html)
        items = _parse_rows(first_html)

        if total is None:
            print(f"warn: total count not found on page 1, returning {len(items)} items only",
                  file=sys.stderr)
            return items

        pages = max(1, math.ceil(total / PAGE_SIZE))
        for page in range(2, pages + 1):
            r = client.get(INDEX_URL, params={"page": page, "orderBy": "date"})
            r.raise_for_status()
            items.extend(_parse_rows(r.text))

        # Deduplicate by rfxId — guards against the rare overlapping page edge case
        seen: set[str] = set()
        unique: list[dict] = []
        for it in items:
            if it["rfxId"] in seen:
                continue
            seen.add(it["rfxId"])
            unique.append(it)
        return unique


def main() -> int:
    items = fetch_all()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(items, indent=2, ensure_ascii=False))
    META_PATH.write_text(json.dumps({
        "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(items),
        "source": "GETS public listing (direct scrape)",
    }, indent=2))
    print(f"wrote {len(items)} items to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

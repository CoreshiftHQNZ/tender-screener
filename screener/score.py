"""Score the raw Apify dump against Coreshift's fit rules.

Reads data/raw.json, writes data/scored.json. The previous scored.json
(if any) is consulted only to compute "new since last run" — an item's
rfxId not present in the prior file is tagged isNew=True.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .dates import NZ, days_until, parse_close_date
from .rules import score_text

RAW_PATH = Path("data/raw.json")
OUT_PATH = Path("data/scored.json")


def _prior_rfx_ids() -> set[str]:
    if not OUT_PATH.exists():
        return set()
    try:
        prior = json.loads(OUT_PATH.read_text())
    except json.JSONDecodeError:
        return set()
    return {str(it.get("rfxId")) for it in prior.get("items", []) if it.get("rfxId")}


def main() -> int:
    raw = json.loads(RAW_PATH.read_text())
    prior_ids = _prior_rfx_ids()
    now = datetime.now(NZ)

    items: list[dict] = []
    for it in raw:
        title = it.get("title") or ""
        fit, reasons = score_text(title)
        close = parse_close_date(it.get("closeDate"))
        items.append({
            "rfxId": str(it.get("rfxId") or ""),
            "referenceNumber": it.get("referenceNumber") or "",
            "title": title,
            "tenderType": it.get("tenderType") or "",
            "tenderTypeCode": it.get("tenderTypeCode") or "",
            "organization": it.get("organization") or "",
            "closeDateRaw": it.get("closeDate") or "",
            "closeDateIso": close.isoformat() if close else None,
            "daysToClose": days_until(close, now),
            "status": it.get("status") or "",
            "url": it.get("url") or "",
            "contractValue": it.get("contractValue") or 0,
            "scrapedAt": it.get("scrapedAt") or "",
            "fitScore": fit,
            "reasons": reasons,
            "isNew": bool(prior_ids) and str(it.get("rfxId")) not in prior_ids,
        })

    items.sort(key=lambda x: (-x["fitScore"], x["daysToClose"] if x["daysToClose"] is not None else 9999))

    OUT_PATH.write_text(json.dumps({
        "generatedAt": now.isoformat(timespec="seconds"),
        "items": items,
    }, indent=2, ensure_ascii=False))
    new_count = sum(1 for it in items if it["isNew"])
    print(f"scored {len(items)} items ({new_count} new) -> {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

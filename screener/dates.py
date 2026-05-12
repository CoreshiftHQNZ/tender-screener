"""Parse the GETS scraper's human-readable close-date format."""

from __future__ import annotations

import math
import re
from datetime import datetime
from zoneinfo import ZoneInfo

NZ = ZoneInfo("Pacific/Auckland")

_PATTERN = re.compile(
    r"(?P<time>\d{1,2}:\d{2})\s*(?P<ampm>AM|PM)\s+"
    r"(?P<day>\d{1,2})\s+(?P<month>\w+)\s+(?P<year>\d{4})",
    re.IGNORECASE,
)


def parse_close_date(s: str | None) -> datetime | None:
    """'4:30 PM 13 May 2026 (Pacific/Auckland UTC+12:00)' -> tz-aware datetime."""
    if not s:
        return None
    m = _PATTERN.match(s.strip())
    if not m:
        return None
    raw = f"{m['time']} {m['ampm'].upper()} {m['day']} {m['month']} {m['year']}"
    try:
        dt = datetime.strptime(raw, "%I:%M %p %d %B %Y")
    except ValueError:
        try:
            dt = datetime.strptime(raw, "%I:%M %p %d %b %Y")
        except ValueError:
            return None
    return dt.replace(tzinfo=NZ)


def days_until(close: datetime | None, now: datetime) -> int | None:
    """Ceiling: 2d 4h remaining shows as 3 days, matching the prototype."""
    if close is None:
        return None
    return math.ceil((close - now).total_seconds() / 86400)

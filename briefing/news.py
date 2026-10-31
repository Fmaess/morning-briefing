"""News aus öffentlichen RSS-Feeds: einsammeln, zeitlich filtern, deduplizieren."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

from . import config

log = logging.getLogger(__name__)


def _parse_time(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def _clean(text: str, limit: int = 300) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _norm_title(title: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", title.lower())[:80]


def collect(now: datetime | None = None, feeds: dict | None = None) -> list[dict]:
    import feedparser

    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=config.NEWS_LOOKBACK_HOURS)
    items, seen = [], set()
    for source, url in (feeds or config.NEWS_FEEDS).items():
        try:
            parsed = feedparser.parse(url, agent="Mozilla/5.0 (morning-briefing)")
        except Exception as exc:  # noqa: BLE001
            log.warning("Feed %s nicht lesbar: %s", source, exc)
            continue
        if not parsed.entries:
            log.warning("Feed %s lieferte keine Einträge", source)
        for e in parsed.entries:
            ts = _parse_time(e)
            if ts and ts < cutoff:
                continue
            title = _clean(e.get("title", ""), 200)
            key = _norm_title(title)
            if not title or key in seen:
                continue
            seen.add(key)
            items.append({
                "source": source,
                "title": title,
                "summary": _clean(e.get("summary", "")),
                "time_utc": ts.isoformat() if ts else None,
            })
    items.sort(key=lambda x: x["time_utc"] or "", reverse=True)
    return items[: config.NEWS_MAX_ITEMS]

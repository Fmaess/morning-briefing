"""Privater Podcast-Feed: Episoden verwalten und feed.xml schreiben."""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

from . import config


def feed_dir() -> Path:
    return Path(config.OUTPUT_DIR) / config.FEED_SECRET_PATH


def feed_url() -> str:
    return f"{config.FEED_BASE_URL}/{config.FEED_SECRET_PATH}/feed.xml"


def _day_of(filename: str) -> str:
    """'briefing-2026-11-02-0652.mp3' -> '2026-11-02' (auch altes Format ohne Uhrzeit)."""
    return filename.removeprefix("briefing-")[:10]


def has_episode_for(day: str) -> bool:
    return any(feed_dir().glob(f"briefing-{day}*.mp3"))


def add_episode(mp3: Path, title: str, notes: str, published: datetime, seconds: float) -> list[dict]:
    d = feed_dir()
    d.mkdir(parents=True, exist_ok=True)
    index_file = d / "episodes.json"
    episodes = json.loads(index_file.read_text("utf-8")) if index_file.exists() else []
    # Eine Folge pro Tag: ältere Version desselben Tages ersetzen
    day = _day_of(mp3.name)
    for old in [e for e in episodes if _day_of(e["file"]) == day and e["file"] != mp3.name]:
        (d / old["file"]).unlink(missing_ok=True)
    episodes = [e for e in episodes if _day_of(e["file"]) != day]
    episodes.append({
        "file": mp3.name,
        "title": title,
        "notes": notes,
        "published": published.isoformat(),
        "seconds": round(seconds),
        "bytes": mp3.stat().st_size,
    })
    episodes.sort(key=lambda e: e["published"], reverse=True)
    for old in episodes[config.FEED_KEEP_EPISODES:]:
        (d / old["file"]).unlink(missing_ok=True)
    episodes = episodes[: config.FEED_KEEP_EPISODES]
    index_file.write_text(json.dumps(episodes, ensure_ascii=False, indent=1), "utf-8")
    write_feed(episodes)
    return episodes


def write_feed(episodes: list[dict] | None = None) -> None:
    d = feed_dir()
    d.mkdir(parents=True, exist_ok=True)
    if episodes is None:
        index_file = d / "episodes.json"
        episodes = json.loads(index_file.read_text("utf-8")) if index_file.exists() else []
    cover = Path(config.FEED_COVER)
    if cover.exists():
        shutil.copyfile(cover, d / "cover.png")
    (d / "feed.xml").write_text(render_feed(episodes), "utf-8")


def render_feed(episodes: list[dict]) -> str:
    base = f"{config.FEED_BASE_URL}/{config.FEED_SECRET_PATH}"
    items = []
    for e in episodes:
        pub = format_datetime(datetime.fromisoformat(e["published"]))
        mins, secs = divmod(int(e["seconds"]), 60)
        items.append(f"""  <item>
   <title>{escape(e["title"])}</title>
   <description>{escape(e["notes"])}</description>
   <enclosure url="{escape(base + "/" + e["file"])}" length="{e["bytes"]}" type="audio/mpeg"/>
   <guid isPermaLink="false">{escape(e["file"] + "#" + e["published"])}</guid>
   <pubDate>{pub}</pubDate>
   <itunes:duration>{mins}:{secs:02d}</itunes:duration>
  </item>""")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
 <channel>
  <title>{escape(config.FEED_TITLE)}</title>
  <link>{escape(base)}</link>
  <description>Private daily macro and European equities briefing</description>
  <language>en</language>
  <itunes:author>{escape(config.FEED_AUTHOR)}</itunes:author>
  <itunes:image href="{escape(base)}/cover.png"/>
  <image><url>{escape(base)}/cover.png</url><title>{escape(config.FEED_TITLE)}</title><link>{escape(base)}</link></image>
  <itunes:category text="Business"><itunes:category text="Investing"/></itunes:category>
  <itunes:type>episodic</itunes:type>
  <itunes:explicit>false</itunes:explicit>
{chr(10).join(items)}
 </channel>
</rss>
"""

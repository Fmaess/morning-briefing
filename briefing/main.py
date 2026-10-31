"""Orchestrierung: Daten -> Skript -> Audio -> Feed.

Aufruf:
  python -m briefing.main            # normaler Lauf (prüft Zeitfenster)
  python -m briefing.main --force    # Zeitfenster ignorieren
  python -m briefing.main --dry-run  # nur Daten sammeln, kein LLM/Audio
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import config

log = logging.getLogger("briefing")

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def in_window(now_local: datetime) -> bool:
    start = now_local.replace(hour=config.RUN_WINDOW_START[0], minute=config.RUN_WINDOW_START[1], second=0)
    end = now_local.replace(hour=config.RUN_WINDOW_END[0], minute=config.RUN_WINDOW_END[1], second=0)
    return now_local.weekday() < 5 and start <= now_local <= end


def safe(step: str, fn, default):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - ein Ausfall soll das Briefing nicht stoppen
        log.exception("Schritt '%s' fehlgeschlagen: %s", step, exc)
        return default


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--feed-only", action="store_true", help="nur feed.xml neu schreiben")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if args.feed_only:
        from . import podcast
        podcast.write_feed()
        log.info("Feed neu geschrieben: %s", podcast.feed_url())
        return 0

    now_local = datetime.now(ZoneInfo(config.TIMEZONE))
    if not args.force and not in_window(now_local):
        log.info("Außerhalb des Zeitfensters (%s) – nichts zu tun.", now_local.strftime("%a %H:%M"))
        return 0

    from . import earnings, market_data, news, podcast, sensitivity

    mp3 = podcast.feed_dir() / f"briefing-{now_local:%Y-%m-%d}.mp3"
    if mp3.exists() and not args.force:
        log.info("Heutige Folge existiert bereits – nichts zu tun.")
        return 0

    date_str = f"{WEEKDAYS[now_local.weekday()]}, {now_local.day} {MONTHS[now_local.month - 1]} {now_local.year}"
    markets = safe("Märkte", market_data.snapshot, {})
    headlines = safe("News", news.collect, [])
    reports = safe("Earnings", earnings.screen, [])
    sens = safe("Sensitivitäten", sensitivity.run, {"ergebnisse": []})

    archive = Path(config.OUTPUT_DIR).parent / "archive" / f"{now_local:%Y-%m-%d}"
    archive.mkdir(parents=True, exist_ok=True)
    (archive / "data.json").write_text(json.dumps(
        {"datum": date_str, "maerkte": markets, "nachrichten": headlines,
         "earnings": reports, "sensitivitaeten": sens},
        ensure_ascii=False, indent=1, default=str), "utf-8")

    if not any(markets.values()) and not headlines:
        log.error("Weder Markt- noch Newsdaten – breche ab.")
        return 1
    if args.dry_run:
        log.info("Dry-Run: Daten in %s", archive)
        return 0

    from . import script_writer, tts

    script, notes = script_writer.write(date_str, markets, headlines, reports, sens)
    (archive / "script.txt").write_text(script + "\n\n===SHOWNOTES===\n" + notes, "utf-8")

    seconds = tts.synthesize(script, mp3)
    podcast.add_episode(mp3, f"Briefing – {date_str}", notes,
                        now_local.astimezone(timezone.utc), seconds)
    log.info("Fertig: %s (%.1f min) – Feed: %s", mp3.name, seconds / 60, podcast.feed_url())
    return 0


if __name__ == "__main__":
    sys.exit(main())

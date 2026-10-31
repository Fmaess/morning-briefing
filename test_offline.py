"""Offline-Tests (ohne Netz): Sensitivitätsmodell, Zeitfenster, Feed, Skript-Split."""
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

from briefing import config, main, podcast, script_writer, sensitivity


def test_ols_recovers_known_beta():
    rng = np.random.default_rng(0)
    x = pd.DataFrame({"f": rng.normal(0, 0.01, 1000)})
    y = pd.Series(0.5 * x["f"] + rng.normal(0, 0.002, 1000), name="y")
    fit = sensitivity.ols(y, x)
    assert abs(fit.betas["f"] - 0.5) < 0.03
    assert fit.tstats["f"] > 20


def test_alignment_lag_rules():
    days = pd.bdate_range("2026-01-05", periods=5)  # Mo-Fr
    raw = pd.DataFrame({"Nikkei": [0.01, 0.02, np.nan, 0.03, 0.04],
                        "S&P 500 (Vortag)": [0.1, 0.2, 0.3, 0.4, 0.5]}, index=days)
    X = sensitivity.align_factors(raw, days)
    # lag 0: gleicher Tag, Feiertag -> 0
    assert X["Nikkei"].tolist() == [0.01, 0.02, 0.0, 0.03, 0.04]
    # lag 1: Wert vom Vortag, am ersten Tag unbekannt
    assert np.isnan(X["S&P 500 (Vortag)"].iloc[0])
    assert X["S&P 500 (Vortag)"].iloc[1:].tolist() == [0.1, 0.2, 0.3, 0.4]


def test_sensitivity_end_to_end_synthetic():
    rng = np.random.default_rng(1)
    days = pd.bdate_range("2023-01-02", periods=800)
    hsi = pd.Series(rng.normal(0, 0.015, len(days)), index=days)
    raw = pd.DataFrame({"Hang Seng": hsi})
    X = sensitivity.align_factors(raw, days)
    # Luxus reagiert stark auf Hang Seng, Versorger gar nicht
    targets = pd.DataFrame({
        "Luxus vs. Markt": 0.6 * hsi + rng.normal(0, 0.005, len(days)),
        "Versorger vs. Markt": rng.normal(0, 0.005, len(days)),
    }, index=days)
    fits = sensitivity.fit_all(targets, X)
    res = sensitivity.explain(fits, pd.Series({"Hang Seng": -0.025}))
    names = [r["ziel"] for r in res]
    assert names == ["Luxus vs. Markt"]
    assert -170 < res[0]["erwarteter_effekt_bp"] < -130


def test_time_window():
    tz = ZoneInfo(config.TIMEZONE)
    assert main.in_window(datetime(2026, 11, 2, 6, 45, tzinfo=tz))       # Montag
    assert not main.in_window(datetime(2026, 11, 2, 5, 45, tzinfo=tz))   # zu früh
    assert not main.in_window(datetime(2026, 11, 1, 6, 45, tzinfo=tz))   # Sonntag


def test_feed_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(config, "FEED_KEEP_EPISODES", 2)
    d = podcast.feed_dir()
    d.mkdir(parents=True)
    for day in (1, 2, 3):
        mp3 = d / f"briefing-2026-11-0{day}.mp3"
        mp3.write_bytes(b"x" * 100)
        podcast.add_episode(mp3, f"Briefing {day} & Co", "Notizen <wichtig>",
                            datetime(2026, 11, day, 6, 50, tzinfo=timezone.utc), 125)
    root = ET.parse(d / "feed.xml").getroot()
    items = root.findall("./channel/item")
    assert len(items) == 2                                    # älteste rotiert raus
    assert not (d / "briefing-2026-11-01.mp3").exists()
    assert items[0].find("title").text == "Briefing 3 & Co"
    assert items[0].find("enclosure").get("url").endswith("/briefing-2026-11-03.mp3")


def test_split_output():
    script, notes = script_writer.split_output("Guten Morgen.\n===SHOWNOTES===\n- Punkt")
    assert script == "Guten Morgen." and notes == "- Punkt"

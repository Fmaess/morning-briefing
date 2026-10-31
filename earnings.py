"""Earnings-Screen: Wer hat seit gestern berichtet, Überraschung vs. Konsens,
Kursreaktion, Schlagzeilen – und optional Call-Transkripte."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

from . import config

log = logging.getLogger(__name__)


def _recent_report(ticker: str, cutoff: datetime) -> dict | None:
    import yfinance as yf

    tk = yf.Ticker(ticker)
    try:
        dates = tk.get_earnings_dates(limit=6)
    except Exception as exc:  # noqa: BLE001
        log.debug("Keine Earnings-Daten für %s: %s", ticker, exc)
        return None
    if dates is None or dates.empty:
        return None
    idx = pd.to_datetime(dates.index, utc=True)
    now = datetime.now(timezone.utc)
    mask = (idx >= cutoff) & (idx <= now)
    if not mask.any():
        return None
    row = dates[mask].iloc[0]
    when = idx[mask][0]

    def num(col):
        v = row.get(col)
        return None if v is None or pd.isna(v) else round(float(v), 3)

    report = {
        "ticker": ticker,
        "time_utc": when.isoformat(),
        "eps_estimate": num("EPS Estimate"),
        "eps_reported": num("Reported EPS"),
        "surprise_pct": num("Surprise(%)"),
        "headlines": _headlines(tk),
    }
    try:
        name = tk.info.get("shortName")
        if name:
            report["name"] = name
    except Exception:  # noqa: BLE001
        pass
    return report


def _headlines(tk, n: int = 3) -> list[str]:
    try:
        news = tk.news or []
    except Exception:  # noqa: BLE001
        return []
    out = []
    for item in news[:n]:
        # yfinance hat das Format mehrfach geändert -> defensiv lesen
        title = item.get("title") or (item.get("content") or {}).get("title")
        if title:
            out.append(title)
    return out


def _price_reaction(reports: list[dict]) -> None:
    from .market_data import download_closes

    tickers = [r["ticker"] for r in reports]
    if not tickers:
        return
    closes = download_closes(tickers, period="5d")
    for r in reports:
        t = r["ticker"]
        if t in closes.columns:
            s = closes[t].dropna()
            if len(s) >= 2:
                r["last_move_pct"] = round((float(s.iloc[-1]) / float(s.iloc[-2]) - 1) * 100, 2)


def fetch_transcript(ticker: str) -> str | None:
    """Optional: Transkript über API Ninjas (Gratis-Key, v. a. US-Werte).
    Andere Quellen lassen sich hier andocken – Rückgabe ist reiner Text."""
    if not config.API_NINJAS_KEY or "." in ticker:
        return None
    try:
        resp = requests.get(
            "https://api.api-ninjas.com/v1/earningstranscript",
            params={"ticker": ticker},
            headers={"X-Api-Key": config.API_NINJAS_KEY},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        log.warning("Transkript %s nicht verfügbar: %s", ticker, exc)
        return None
    if isinstance(data, list):
        data = data[0] if data else {}
    text = data.get("transcript") if isinstance(data, dict) else None
    return text or None


def screen(now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=config.EARNINGS_LOOKBACK_HOURS)
    reports = []
    for t in config.EARNINGS_UNIVERSE:
        r = _recent_report(t, cutoff)
        if r:
            reports.append(r)
    _price_reaction(reports)
    for r in reports:
        text = fetch_transcript(r["ticker"])
        if text:
            # Q&A ist meist der aufschlussreichste Teil -> Ende bevorzugen
            r["transcript_excerpt"] = text[:4000] + "\n[...]\n" + text[-6000:] if len(text) > 10000 else text
    log.info("Earnings seit gestern: %s", ", ".join(r["ticker"] for r in reports) or "keine")
    return reports

"""Marktdaten über yfinance. Alle Zahlen im Briefing kommen von hier –
das Sprachmodell bekommt sie nur zur Interpretation, erfindet keine eigenen."""
from __future__ import annotations

import logging

import pandas as pd

from . import config

log = logging.getLogger(__name__)


def download_closes(tickers: list[str], period: str = "10d") -> pd.DataFrame:
    """Tagesschlusskurse (bzw. letzter Kurs am laufenden Tag) als DataFrame."""
    import yfinance as yf

    data = yf.download(
        tickers, period=period, interval="1d", auto_adjust=True,
        progress=False, group_by="column", threads=True,
    )
    if data is None or data.empty:
        return pd.DataFrame()
    closes = data["Close"] if isinstance(data.columns, pd.MultiIndex) else data[["Close"]]
    if not isinstance(closes, pd.DataFrame):
        closes = closes.to_frame()
    if len(tickers) == 1:
        closes.columns = tickers
    missing = [t for t in tickers if t not in closes.columns or closes[t].dropna().empty]
    if missing:
        log.warning("Keine Daten für: %s", ", ".join(missing))
    return closes


def summarize_series(name: str, ticker: str, s: pd.Series, mode: str = "ret") -> dict | None:
    s = s.dropna()
    if len(s) < 2:
        return None
    last, prev = float(s.iloc[-1]), float(s.iloc[-2])
    row = {"name": name, "ticker": ticker, "last": round(last, 4),
           "as_of": str(s.index[-1].date())}
    if mode == "diff":  # Renditen: Veränderung in Basispunkten
        row["change_bp"] = round((last - prev) * 100, 1)
    else:
        row["change_pct"] = round((last / prev - 1) * 100, 2)
        if len(s) >= 6:
            row["change_5d_pct"] = round((last / float(s.iloc[-6]) - 1) * 100, 2)
    return row


def snapshot() -> dict:
    """Überblick über alle Märkte, gruppiert wie im Briefing."""
    groups = {
        "asien": (config.ASIA, "ret"),
        "usa": (config.US, "ret"),
        "europa": (config.EUROPE, "ret"),
        "zinsen": (config.RATES, None),
        "rohstoffe": (config.COMMODITIES, "ret"),
        "devisen": (config.FX, "ret"),
        "volatilitaet": (config.VOL, "ret"),
    }
    all_tickers = sorted({t for g, _ in groups.values() for t in g.values()})
    closes = download_closes(all_tickers)
    out: dict[str, list] = {}
    for key, (mapping, mode) in groups.items():
        rows = []
        for name, t in mapping.items():
            if t not in closes.columns:
                continue
            m = mode or ("diff" if "Rendite" in name else "ret")
            r = summarize_series(name, t, closes[t], m)
            if r:
                rows.append(r)
        out[key] = rows
    return out

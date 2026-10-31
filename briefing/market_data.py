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
    try:
        out["zinsen"].extend(bundesbank_yields())
    except Exception as exc:  # noqa: BLE001 - Bundesbank-Ausfall soll nichts stoppen
        log.warning("Bundesbank-Renditen nicht verfügbar: %s", exc)
    return out


# --- Bundesbank: tägliche Umlaufrenditen von Bundeswertpapieren ---------------

def parse_sdmx_generic(xml_text: str) -> pd.Series:
    """Liest Beobachtungen (Datum -> Wert) aus SDMX-GenericData-XML."""
    import xml.etree.ElementTree as ET

    def local(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    obs = {}
    for el in ET.fromstring(xml_text).iter():
        if local(el.tag) != "Obs":
            continue
        date = value = None
        for child in el:
            if local(child.tag) == "ObsDimension":
                date = child.get("value")
            elif local(child.tag) == "ObsValue":
                value = child.get("value")
        if date and value not in (None, "", "NaN"):
            obs[pd.Timestamp(date)] = float(value)
    return pd.Series(obs, dtype=float).sort_index()


def bundesbank_yields() -> list[dict]:
    import requests

    rows = []
    for name, key in config.BUNDESBANK_YIELDS.items():
        resp = requests.get(
            f"{config.BUNDESBANK_API}/data/BBSIS/{key}",
            params={"lastNObservations": 10},
            headers={"Accept": "application/vnd.sdmx.genericdata+xml;version=2.1"},
            timeout=30,
        )
        resp.raise_for_status()
        r = summarize_series(name, f"BBSIS.{key}", parse_sdmx_generic(resp.text), "diff")
        if r:
            r["quelle"] = "Deutsche Bundesbank (Umlaufrendite, Stand Vortag)"
            rows.append(r)
    return rows

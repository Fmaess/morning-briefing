"""Sensitivitätsmodell: Wie reagieren europäische Sektoren historisch auf
Übernacht-Bewegungen (Asien, US-Vortag, Öl, Renditen, Yen)?

Für jeden Sektor wird die Tagesrendite relativ zum Stoxx 600 per OLS auf die
Faktoren regressiert, für den Gesamtmarkt die absolute Rendite. Mit den
heutigen Faktorwerten ergibt das einen erwarteten Effekt – ins Briefing kommen
nur Effekte mit robuster Statistik (|t| >= Schwelle) und relevanter Größe.

Wichtig: Das ist eine Daumenregel aus Tagesdaten (Schluss-zu-Schluss), keine
Prognose der Eröffnung. Erklärungskraft einzelner Tage ist typischerweise gering.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import config

log = logging.getLogger(__name__)


@dataclass
class Fit:
    target: str
    betas: pd.Series
    tstats: pd.Series
    r2: float
    n: int


def ols(y: pd.Series, X: pd.DataFrame) -> Fit:
    df = pd.concat([y.rename("_y"), X], axis=1).dropna()
    yv = df["_y"].to_numpy()
    Xv = np.column_stack([np.ones(len(df)), df[X.columns].to_numpy()])
    coef, *_ = np.linalg.lstsq(Xv, yv, rcond=None)
    resid = yv - Xv @ coef
    dof = max(len(df) - Xv.shape[1], 1)
    sigma2 = resid @ resid / dof
    cov = sigma2 * np.linalg.pinv(Xv.T @ Xv)
    se = np.sqrt(np.diag(cov))
    r2 = 1 - (resid @ resid) / max(((yv - yv.mean()) ** 2).sum(), 1e-12)
    names = ["const", *X.columns]
    return Fit(y.name, pd.Series(coef, names), pd.Series(coef / se, names), float(r2), len(df))


def align_factors(raw: pd.DataFrame, eu_index: pd.DatetimeIndex) -> pd.DataFrame:
    """Faktoren auf europäische Handelstage ausrichten.

    raw: Spalten = Faktorname, Werte = Rendite bzw. Renditeänderung auf dem
    eigenen Handelskalender des Faktors.
    lag 0 -> Wert am selben Kalendertag (0, falls dort nicht gehandelt)
    lag 1 -> letzter verfügbarer Wert VOR dem europäischen Handelstag
    """
    out = {}
    for name, (_, lag, _) in config.SENS_FACTORS.items():
        if name not in raw.columns:
            continue
        s = raw[name].dropna()
        if lag == 0:
            out[name] = s.reindex(eu_index).fillna(0.0)
        else:
            shifted = s.copy()
            shifted.index = shifted.index + pd.Timedelta(days=1)  # "strikt vorher"
            out[name] = shifted.reindex(eu_index, method="ffill")
    return pd.DataFrame(out, index=eu_index)


def factor_returns(closes: pd.DataFrame) -> pd.DataFrame:
    cols = {}
    for name, (ticker, _, kind) in config.SENS_FACTORS.items():
        if ticker not in closes.columns:
            continue
        s = closes[ticker].dropna()
        cols[name] = s.diff() if kind == "diff" else s.pct_change()
    return pd.DataFrame(cols)


def todays_factors(raw: pd.DataFrame, today: pd.Timestamp) -> pd.Series:
    vals = {}
    for name, (_, lag, _) in config.SENS_FACTORS.items():
        if name not in raw.columns:
            continue
        s = raw[name].dropna()
        if lag == 0:
            vals[name] = float(s.loc[s.index.normalize() == today.normalize()].iloc[-1]) \
                if (s.index.normalize() == today.normalize()).any() else 0.0
        else:
            prior = s[s.index.normalize() < today.normalize()]
            vals[name] = float(prior.iloc[-1]) if len(prior) else 0.0
    return pd.Series(vals)


def fit_all(targets: pd.DataFrame, X: pd.DataFrame) -> list[Fit]:
    fits = []
    for col in targets.columns:
        fit = ols(targets[col], X)
        if fit.n >= 120:
            fits.append(fit)
    return fits


def explain(fits: list[Fit], today: pd.Series) -> list[dict]:
    """Erwarteten Effekt je Ziel berechnen und nur robuste Treiber berichten."""
    rows = []
    for f in fits:
        drivers = []
        total = 0.0
        for factor, x in today.items():
            if factor not in f.betas:
                continue
            impact_bp = float(f.betas[factor] * x * 1e4)
            if abs(f.tstats[factor]) >= config.SENS_MIN_TSTAT and abs(impact_bp) >= config.SENS_MIN_IMPACT_BP:
                drivers.append({"faktor": factor, "effekt_bp": round(impact_bp, 0),
                                "t_stat": round(float(f.tstats[factor]), 1)})
            total += impact_bp
        if drivers:
            rows.append({
                "ziel": f.target,
                "erwarteter_effekt_bp": round(total, 0),
                "treiber": sorted(drivers, key=lambda d: -abs(d["effekt_bp"])),
                "r2": round(f.r2, 2),
            })
    return sorted(rows, key=lambda r: -abs(r["erwarteter_effekt_bp"]))


def run(today: pd.Timestamp | None = None) -> dict:
    from .market_data import download_closes

    today = today or pd.Timestamp.now(tz=config.TIMEZONE).tz_localize(None)
    sector_tickers = list(config.EU_SECTORS.values())
    factor_tickers = [t for t, _, _ in config.SENS_FACTORS.values()]
    tickers = sorted(set(sector_tickers + factor_tickers + config.LUXURY_BASKET + [config.EU_MARKET_PROXY]))
    closes = download_closes(tickers, period="4y")
    if closes.empty or config.EU_MARKET_PROXY not in closes.columns:
        log.warning("Sensitivitätsmodell: keine Daten")
        return {"hinweis": "keine Daten", "ergebnisse": []}
    idx = pd.to_datetime(closes.index)
    if idx.tz is not None:
        idx = idx.tz_convert(None)
    closes.index = idx.normalize()
    closes = closes[~closes.index.duplicated(keep="last")]

    rets = pd.DataFrame({c: closes[c].dropna().pct_change() for c in closes.columns})
    market = rets[config.EU_MARKET_PROXY].rename("Stoxx 600 (gesamt)")
    targets = {"Stoxx 600 (gesamt)": market}
    for name, t in config.EU_SECTORS.items():
        if t in rets.columns:
            targets[f"{name} vs. Markt"] = rets[t] - rets[config.EU_MARKET_PROXY]
    lux = [t for t in config.LUXURY_BASKET if t in rets.columns]
    if lux:
        targets["Luxus vs. Markt"] = rets[lux].mean(axis=1) - rets[config.EU_MARKET_PROXY]
    targets = pd.DataFrame(targets)

    # Nur abgeschlossene europäische Tage zum Schätzen, letztes Fenster
    eu_days = closes[config.EU_MARKET_PROXY].dropna().index
    eu_days = eu_days[eu_days < today.normalize()][-config.SENS_LOOKBACK_DAYS:]
    raw = factor_returns(closes)
    X = align_factors(raw, eu_days)
    fits = fit_all(targets.reindex(eu_days), X)
    today_x = todays_factors(raw, today)
    return {
        "hinweis": "Historische Daumenregel aus Tagesdaten, keine Prognose der Eröffnung.",
        # Renditen: Anteil -> %, Renditeänderungen: Prozentpunkte -> bp (beides x100)
        "faktoren_heute": {k: round(v * 100, 2) for k, v in today_x.items()},
        "faktoren_einheit": "Renditen in %, Renditeänderungen in bp",
        "ergebnisse": explain(fits, today_x),
    }

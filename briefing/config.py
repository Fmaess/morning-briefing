"""Zentrale Konfiguration des Morning Briefings.

Alle Ticker sind Yahoo-Finance-Symbole. Ticker, die beim Abruf keine Daten
liefern, werden automatisch übersprungen und im Log gemeldet – beim ersten
Lauf also einmal das Log prüfen.
"""
import os

TIMEZONE = "Europe/Berlin"

# Startfenster (Lokalzeit). Der Workflow startet zweimal (wegen Sommer-/
# Winterzeit); Läufe außerhalb des Fensters oder wenn die heutige Folge schon
# existiert, brechen sofort ab. Der zweite Lauf dient so auch als Backup.
RUN_WINDOW_START = (6, 30)
RUN_WINDOW_END = (8, 30)

# --- Märkte ------------------------------------------------------------------
ASIA = {
    "Nikkei 225": "^N225",
    "Hang Seng": "^HSI",
    "Shanghai Composite": "000001.SS",
    "Kospi": "^KS11",
    "ASX 200": "^AXJO",
}
US = {
    "S&P 500": "^GSPC",
    "Nasdaq 100": "^NDX",
    "S&P 500 Future": "ES=F",
    "Nasdaq Future": "NQ=F",
}
EUROPE = {
    "Euro Stoxx 50": "^STOXX50E",
    "DAX": "^GDAXI",
    "Stoxx 600": "^STOXX",
}
# Renditen: Yahoo liefert ^TNX/^FVX in Prozent. Bund-Rendite und Bund-Future
# liefert Yahoo nicht (erster Lauf geprüft) – Bunds kommen bisher nur über News.
RATES = {
    "US 10J Rendite": "^TNX",
    "US 5J Rendite": "^FVX",
}
COMMODITIES = {
    "Brent": "BZ=F",
    "TTF Gas": "TTF=F",
    "Gold": "GC=F",
    "Kupfer": "HG=F",
}
FX = {
    "EUR/USD": "EURUSD=X",
    "USD/JPY": "JPY=X",
    "USD/CNY": "CNY=X",
}
VOL = {"VIX": "^VIX"}

# Europäische Sektoren: iShares STOXX Europe 600 Sektor-ETFs auf Xetra.
# Beim ersten Lauf im Log prüfen, ob alle Ticker Daten liefern.
EU_SECTORS = {
    "Banken": "EXV1.DE",
    "Öl & Gas": "EXH1.DE",
    "Rohstoffe": "EXV6.DE",
    "Autos": "EXV5.DE",
    "Technologie": "EXV3.DE",
    "Gesundheit": "EXV4.DE",
    "Versorger": "EXH9.DE",
    "Versicherungen": "EXH5.DE",
    "Industrie": "EXH4.DE",
    "Telekom": "EXV2.DE",
    "Immobilien": "EXI5.DE",
}
# Für Luxus gibt es keinen Sektor-ETF -> gleichgewichteter Korb
LUXURY_BASKET = ["MC.PA", "RMS.PA", "KER.PA", "CFR.SW"]
EU_MARKET_PROXY = "^STOXX"

# Übernacht-Faktoren für das Sensitivitätsmodell.
# lag=0: am selben Morgen schon bekannt (Asien), lag=1: Vortagesschluss.
SENS_FACTORS = {
    "Nikkei": ("^N225", 0, "ret"),
    "Hang Seng": ("^HSI", 0, "ret"),
    "S&P 500 (Vortag)": ("^GSPC", 1, "ret"),
    "Brent (Vortag)": ("BZ=F", 1, "ret"),
    "US 10J Rendite (Vortag)": ("^TNX", 1, "diff"),
    "USD/JPY (Vortag)": ("JPY=X", 1, "ret"),
}
SENS_LOOKBACK_DAYS = 750      # ca. 3 Jahre Handelstage
SENS_MIN_TSTAT = 2.0          # nur robuste Zusammenhänge ins Briefing
SENS_MIN_IMPACT_BP = 15       # nur erwähnen, wenn erwarteter Effekt >= 15 bp

# --- Earnings ----------------------------------------------------------------
# Universum, dessen Ergebnisse vom Vortag/über Nacht gescreent werden.
EARNINGS_UNIVERSE = [
    # Europa
    "ASML.AS", "SAP.DE", "MC.PA", "SIE.DE", "TTE.PA", "ALV.DE", "SAN.PA",
    "OR.PA", "AIR.PA", "SU.PA", "DTE.DE", "IBE.MC", "BNP.PA", "INGA.AS",
    "MBG.DE", "BMW.DE", "VOW3.DE", "BAS.DE", "BAYN.DE", "IFX.DE", "ADS.DE",
    "RMS.PA", "KER.PA", "ENEL.MI", "ISP.MI", "UCG.MI", "SAF.PA", "DB1.DE",
    "MUV2.DE", "ABI.BR", "NOVO-B.CO", "NESN.SW", "ROG.SW", "NOVN.SW",
    "SHEL.L", "AZN.L", "HSBA.L", "ULVR.L", "BP.L", "RIO.L",
    # US Mega Caps (Read-Across für Europa)
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "JPM", "XOM",
    "LLY", "AVGO", "WMT", "CAT",
]
EARNINGS_LOOKBACK_HOURS = 30

# --- News (RSS) --------------------------------------------------------------
# Nur öffentliche Feeds. Feeds, die nicht erreichbar sind, werden übersprungen.
NEWS_FEEDS = {
    "EZB": "https://www.ecb.europa.eu/rss/press.html",
    "Fed": "https://www.federalreserve.gov/feeds/press_all.xml",
    "CNBC World": "https://www.cnbc.com/id/100727362/device/rss/rss.html",
    "CNBC Earnings": "https://www.cnbc.com/id/15839135/device/rss/rss.html",
    "MarketWatch": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "Investing.com": "https://www.investing.com/rss/news_14.rss",
    "Nikkei Asia": "https://asia.nikkei.com/rss/feed/nar",
}
NEWS_LOOKBACK_HOURS = 18
NEWS_MAX_ITEMS = 60

# --- Sprachmodell ------------------------------------------------------------
LLM_MODEL = os.getenv("BRIEFING_LLM_MODEL", "claude-sonnet-5-5")
LLM_MAX_TOKENS = 16000        # deckt Nachdenken + Skript ab
LLM_EFFORT = "medium"         # low / medium / high – höher = gründlicher, teurer
SCRIPT_MIN_WORDS = 300        # kürzere Skripte gelten als Fehler (keine Mini-Folge)
SCRIPT_TARGET_MINUTES = 8

# --- Vertonung (lokal, kostenlos) --------------------------------------------
PIPER_VOICE = os.getenv("PIPER_VOICE", "de_DE-thorsten-high")
PIPER_VOICE_DIR = os.getenv("PIPER_VOICE_DIR", "voices")

# --- Podcast-Feed ------------------------------------------------------------
FEED_TITLE = "Morning Briefing – Makro & Europa"
FEED_AUTHOR = "Privat"
FEED_BASE_URL = os.getenv("FEED_BASE_URL", "https://example.github.io/briefing-feed").rstrip("/")
FEED_SECRET_PATH = os.getenv("FEED_SECRET_PATH", "changeme")
FEED_KEEP_EPISODES = 14
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "public")

# --- Optionale Transkript-Quelle --------------------------------------------
API_NINJAS_KEY = os.getenv("API_NINJAS_KEY", "")

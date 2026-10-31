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
# liefert Yahoo nicht – Bunds kommen von der Bundesbank (siehe unten).
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

# Bundesbank: tägliche Umlaufrenditen börsennotierter Bundeswertpapiere nach
# Restlaufzeit (Datenreihe BBSIS). Veröffentlichung mit einem Tag Verzug.
BUNDESBANK_API = "https://api.statistiken.bundesbank.de/rest"
BUNDESBANK_YIELDS = {
    "Bund 2J Rendite": "D.I.ZAR.ZI.EUR.S1311.B.A604.R02XX.R.A.A._Z._Z.A",
    "Bund 10J Rendite": "D.I.ZAR.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A",
}

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
    "Kospi": ("^KS11", 0, "ret"),
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
SCRIPT_MIN_WORDS = 300       # kürzere Skripte gelten als Fehler (keine Mini-Folge)
SCRIPT_TARGET_MINUTES = 7
# Begrüßung und Verabschiedung: wechseln täglich (am selben Tag stabil).
# Für Montag/Freitag gibt es eigene Sprüche; alle anderen Tage ziehen aus der
# allgemeinen Liste. Einfach erweitern oder kürzen.
GREETINGS = [
    "Morning, champ!",
    "Rise and grind, champ. The market waits for no one.",
    "Good morning, legend. Let's go find some alpha.",
    "Morning, big dog. Coffee in hand? Good. Let's do this.",
    "What's up, chief. Asia didn't sleep, so neither did we.",
    "Morning, hotshot. Let's see who got rich overnight.",
    "Good morning, future PM. Your desk is waiting.",
    "Morning, Gordon Gekko. Greed is good, but let's check the data first.",
    "Wakey wakey, champ. Futures are moving.",
    "Top of the morning, maestro. Let's beat the benchmark.",
    "Morning, sharpshooter. Sharpe ratio ready?",
]
GREETINGS_BY_WEEKDAY = {
    "Monday": [
        "Happy Monday, champ. New week, new alpha.",
        "Morning, champ. It's Monday. Let's pretend we're excited.",
        "Monday again, legend. Weekend's over, the market's back.",
    ],
    "Friday": [
        "It's Friday, champ! One more session, then the weekend.",
        "Happy Friday, legend. Let's close this week out strong.",
        "Friday, big dog. Don't get caught long into the weekend without a plan.",
    ],
}
SIGNOFFS = [
    "That's your briefing. Go get 'em, champ.",
    "That's it from me. Buy low, sell high, and don't forget to hydrate.",
    "That's the tape. Now go make your risk manager proud.",
    "That's all. Stay humble, stay hedged.",
    "Briefing over. Go show the market who's boss.",
    "That's your edge for today. Use it wisely, champ.",
]
SIGNOFFS_BY_WEEKDAY = {
    "Friday": [
        "That's the last briefing of the week. Have a great weekend, champ.",
        "That's a wrap for the week. Square your book, then open a cold one.",
    ],
}

# Technik des Tages: wird im Briefing bewusst eingesetzt, aber nie benannt
# (passives Lernen, kein Lern-Segment). Rotiert täglich.
CRAFT_CORNER = True
CRAFT_TECHNIQUES = [
    ("And-But-Therefore", "setup with 'and', tension with 'but', consequence with 'therefore'"),
    ("Start with the end", "state the conclusion first so the listener knows where you are going"),
    ("The pause", "silence right before the key point makes it land"),
    ("Rule of three", "group ideas in threes; it feels complete and is easy to remember"),
    ("Contrast", "put two things side by side, this versus that, to sharpen both"),
    ("Specificity", "one concrete detail beats three vague adjectives"),
    ("The callback", "end by returning to the opening image or phrase to close the loop"),
    ("The 'so what'", "after every fact, say why it matters to the listener"),
    ("Analogy", "explain the unfamiliar through something the listener already knows"),
    ("The open question", "pose the question the listener is already asking, then answer it"),
    ("Steelman the other side", "state the strongest counter-argument fairly before your view"),
    ("Short sentence after long", "a long build-up followed by a three-word sentence hits hard"),
    ("The hidden variable", "name the assumption everyone takes for granted and question it"),
    ("Signposting", "tell the listener where you are in the story: first, but here's the twist, bottom line"),
]

# --- Vertonung (lokal, kostenlos) --------------------------------------------
# "kokoro" (Standard, natürlicher, Englisch) oder "piper" (kann Deutsch)
TTS_ENGINE = os.getenv("TTS_ENGINE", "kokoro")
TTS_SPEED = 1.12              # 0.9 = ruhiger, 1.1 = flotter
# Tonhöhe: 1.0 = original, 0.95 = 5 % tiefer (Sprechtempo bleibt gleich)
TTS_PITCH = 0.95
PARAGRAPH_PAUSE_S = 0.45      # Pause zwischen Absätzen in Sekunden
DRAMATIC_PAUSE_S = 0.9       # Pause bei [pause]-Markern im Skript

# Kokoro: Stimmen-Mix aus männlichen US-Stimmen. Gewichte werden normiert.
# Weitere Stimmen: am_onyx, am_puck, am_echo, am_eric, am_liam (US),
# bm_george, bm_fable, bm_daniel, bm_lewis (UK; dann KOKORO_LANG = "en-gb")
KOKORO_VOICE_MIX = {"am_michael": 0.75, "am_onyx": 0.25}
KOKORO_LANG = "en-us"
KOKORO_MODEL_DIR = os.getenv("KOKORO_MODEL_DIR", "models")

# Piper (Alternative)
PIPER_VOICE = os.getenv("PIPER_VOICE", "de_DE-thorsten-high")
PIPER_VOICE_DIR = os.getenv("PIPER_VOICE_DIR", "voices")

# --- Podcast-Feed ------------------------------------------------------------
FEED_TITLE = "Morning Briefing – Macro & Europe"
FEED_AUTHOR = "Morning Briefing"
FEED_COVER = "assets/cover.png"
FEED_BASE_URL = os.getenv("FEED_BASE_URL", "https://example.github.io/briefing-feed").rstrip("/")
FEED_SECRET_PATH = os.getenv("FEED_SECRET_PATH", "changeme")
FEED_KEEP_EPISODES = 14
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "public")

# --- Optionale Transkript-Quelle --------------------------------------------
API_NINJAS_KEY = os.getenv("API_NINJAS_KEY", "")

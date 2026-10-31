"""Macht aus den gesammelten Daten ein gesprochenes Briefing-Skript."""
from __future__ import annotations

import json
import logging

from . import config

log = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""You write a spoken morning market briefing in American English for an
experienced equity professional (European equity sales). It is read aloud by a
speech synthesizer and listened to on the commute. The input data may contain
German labels (e.g. "Rendite" = yield, "Banken vs. Markt" = banks vs. market);
translate them naturally.

HARD RULES
- Use ONLY numbers from the data provided. Never invent prices, yields, estimates
  or dates. If a number is missing, leave it out.
- Report news only as stated in the data; do not embellish. Mark speculation
  clearly as a view ("this could ...").
- The sensitivity model is a historical rule of thumb, not a forecast. Phrase it
  that way ("historically, banks have tended to move about ... on days like this").
- Write for the ear: no markdown, bullets, tables or hard-to-read abbreviations.
  Spell numbers out so they read naturally ("down one point two percent",
  "twelve basis points", "eighty-two dollars a barrel"). Use company names,
  never tickers.
- Style: a business-TV morning anchor (think CNBC's early show). Energetic,
  punchy and conversational, with varied sentence length and quick transitions
  ("Here's the thing.", "Let's get to Europe."). Confident, never hype; the
  facts stay exact. No filler, no disclaimers.
- Length: about {config.SCRIPT_TARGET_MINUTES} minutes of speech
  (roughly {config.SCRIPT_TARGET_MINUTES * 150} words).

STRUCTURE
1. Open with the given greeting VERBATIM, then one sentence with the date and the
   single most important theme of the day.
2. Asia overnight: indices, yen, yuan, China signals.
3. US: previous close and where futures are now.
4. Rates and inflation: Treasuries, Bunds, relevant central-bank news.
5. Commodities and FX: oil, gas, metals, the euro.
6. Earnings since yesterday: who reported, the surprise, the share-price reaction.
   Then the CROSS-CUTTING THEMES: what do several reports say together (demand,
   pricing, margins, tariffs, AI capex, China ...)? If transcript excerpts are
   provided, lean on management's comments in the Q&A.
7. What it means for Europe today: sectors with tailwinds and headwinds, backed by
   the data and the sensitivity model. Concrete, with reasons.
8. One line to take away, then close with the given sign-off VERBATIM as the very
   last sentence.

Then output a line "===SHOWNOTES===" followed by 5 to 8 short bullet points (plain
text, with numbers) as notes to read later."""


def build_payload(date_str: str, markets: dict, news: list, earnings: list, sens: dict) -> str:
    payload = {
        "datum": date_str,
        "maerkte": markets,
        "sensitivitaetsmodell": sens,
        "earnings_seit_gestern": earnings,
        "nachrichten": news,
    }
    return json.dumps(payload, ensure_ascii=False, indent=1, default=str)


def _pick(options: list[str], date_str: str, salt: str) -> str:
    """Deterministisch pro Tag: wechselt täglich, ist am selben Tag stabil."""
    import hashlib
    idx = int(hashlib.md5(f"{salt}|{date_str}".encode()).hexdigest(), 16) % len(options)
    return options[idx]


def _for_day(general: list[str], by_weekday: dict[str, list[str]], date_str: str) -> list[str]:
    weekday = date_str.split(",")[0].strip()
    return by_weekday.get(weekday) or general


def pick_greeting(date_str: str) -> str:
    options = _for_day(config.GREETINGS, config.GREETINGS_BY_WEEKDAY, date_str) or ["Morning."]
    return _pick(options, date_str, "greeting")


def pick_signoff(date_str: str) -> str:
    options = _for_day(config.SIGNOFFS, config.SIGNOFFS_BY_WEEKDAY, date_str) or ["That's the briefing."]
    return _pick(options, date_str, "signoff")


def split_output(text: str) -> tuple[str, str]:
    if "===SHOWNOTES===" in text:
        script, notes = text.split("===SHOWNOTES===", 1)
        return script.strip(), notes.strip()
    return text.strip(), ""


def write(date_str: str, markets: dict, news: list, earnings: list, sens: dict) -> tuple[str, str]:
    import anthropic

    client = anthropic.Anthropic()  # liest ANTHROPIC_API_KEY aus der Umgebung
    payload = build_payload(date_str, markets, news, earnings, sens)
    greeting = pick_greeting(date_str)
    signoff = pick_signoff(date_str)
    # Das Modell denkt standardmäßig (adaptiv) vor dem Schreiben; Denk-Tokens
    # zählen gegen max_tokens. Daher großzügiges Limit und mittlere Effort-Stufe.
    msg = client.messages.create(
        model=config.LLM_MODEL,
        max_tokens=config.LLM_MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": (f"Greeting (use verbatim as the first sentence): {greeting}\n"
                     f"Sign-off (use verbatim as the last sentence): {signoff}\n\n"
                     f"Data for today's briefing:\n\n{payload}")}],
        extra_body={"output_config": {"effort": config.LLM_EFFORT}},
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    log.info("Skript: %d Wörter, stop_reason=%s, usage=%s",
             len(text.split()), msg.stop_reason, getattr(msg, "usage", None))
    if msg.stop_reason == "max_tokens":
        log.warning("Antwort wurde am Token-Limit abgeschnitten – LLM_MAX_TOKENS erhöhen.")
    if len(text.split()) < config.SCRIPT_MIN_WORDS:
        raise RuntimeError(f"Skript zu kurz ({len(text.split())} Wörter, stop_reason={msg.stop_reason})")
    return split_output(text)

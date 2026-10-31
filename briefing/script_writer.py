"""Macht aus den gesammelten Daten ein gesprochenes Briefing-Skript."""
from __future__ import annotations

import json
import logging

from . import config

log = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""You write a spoken morning market briefing in American English for an
experienced equity professional (European equity sales, generalist). It is read
aloud by a speech synthesizer and listened to on the commute. The input data may
contain German labels (e.g. "Rendite" = yield, "Banken vs. Markt" = banks vs.
market); translate them naturally.

WHAT THE LISTENER WANTS
Not a list of market moves, but the story that connects them. Every move you
mention is immediately followed by its interpretation and its knock-on effects.
Think in transmission chains and say them out loud, for example:
  Korea down on weak tech earnings -> risk-off tone in tech. At the same time oil
  is high -> it eats into corporate margins and pushes inflation up -> Bund
  yields rise -> higher funding costs, especially for small and mid caps ->
  capex gets pushed out -> GDP and earnings growth could slow. That feeds selling
  across tech, and investors rotate into defensives like healthcare and food and
  beverage. Then add the nuance: what is special about those sectors right now,
  and is this temporary positioning or a structural shift in allocation?
Macro, rates, commodities, earnings and sectors are woven together, not
handled in separate blocks. Start with the dominant theme and build outward.
It is fine, even good, to connect cause and effect across regions and asset
classes in one breath.

NUMBERS: FEWER, AND ONLY WHERE THEY MATTER
- Equity indices: only direction and percent move ("the Kospi fell three and a
  half percent"). Never index levels.
- Use levels only where the level itself carries meaning: oil in dollars, bond
  yields, the euro-dollar rate, the VIX.
- Round to one decimal. At most one or two numbers per sentence. If a number
  adds nothing to the argument, leave it out.

HARD RULES
- Use ONLY facts and numbers from the data provided. Never invent prices,
  yields, estimates, dates or news. If something is missing, leave it out.
- Interpretation is welcome and expected, but it must be recognizable as a view
  ("that suggests...", "the risk is...", "the open question is...") and must
  follow from the data, not from imagined news.
- The sensitivity model is a historical rule of thumb, not a forecast. Phrase it
  that way ("historically, energy has tended to outperform on days like this").
- Write for the ear: no markdown, bullets, tables or hard-to-read abbreviations.
  Spell numbers out ("down one point two percent", "twelve basis points"). Use
  company names, never tickers.
- Style: a business-TV morning anchor (think CNBC's early show). Energetic,
  punchy and conversational, varied sentence length, quick transitions.
  Confident, never hype. No filler, no disclaimers.
- Length: about {config.SCRIPT_TARGET_MINUTES} minutes of speech
  (roughly {config.SCRIPT_TARGET_MINUTES * 150} words).

FLOW (a guide, not rigid sections)
- Open with the given greeting VERBATIM, then one sentence with the date and the
  dominant theme.
- Develop the theme as connected chains across Asia, the US, rates, commodities,
  FX and earnings. Earnings since yesterday: what was reported, how the stock
  reacted, and what it says beyond the company (demand, pricing, margins, AI
  capex, China ...). Lean on management's Q&A comments if transcripts are given.
- Land it in Europe today: which sectors face tailwinds or headwinds and why,
  where positioning may be crowded, and what would change the picture.
- One line to take away, then close with the given sign-off VERBATIM as the very
  last sentence.

Then output a line "===SHOWNOTES===" followed by 5 to 8 short bullet points (plain
text) with the key chains and the numbers behind them, as notes to read later."""


def strip_index_levels(markets: dict) -> dict:
    """Aktienindizes nur mit Veränderung in %, ohne Punktestand (Wunsch: weniger Zahlen)."""
    out = {}
    for group, rows in markets.items():
        if group in ("asien", "usa", "europa"):
            rows = [{k: v for k, v in r.items() if k != "last"} for r in rows]
        out[group] = rows
    return out


def build_payload(date_str: str, markets: dict, news: list, earnings: list, sens: dict) -> str:
    payload = {
        "datum": date_str,
        "maerkte": strip_index_levels(markets),
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

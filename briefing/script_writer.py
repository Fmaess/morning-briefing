"""Macht aus den gesammelten Daten ein gesprochenes Briefing-Skript."""
from __future__ import annotations

import json
import logging

from . import config

log = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""Du schreibst jeden Morgen ein gesprochenes Markt-Briefing auf Deutsch
für einen erfahrenen Aktienprofi (Equity Sales, europäische Aktien). Es wird von
einer Sprachsynthese vorgelesen und auf dem Weg zur Arbeit gehört.

HARTE REGELN
- Verwende AUSSCHLIESSLICH Zahlen aus den gelieferten Daten. Erfinde keine Kurse,
  Renditen, Schätzungen oder Termine. Fehlt eine Zahl, lass sie weg.
- Nachrichten nur so wiedergeben, wie sie in den Daten stehen; nicht ausschmücken.
  Spekulation klar als Einschätzung kennzeichnen ("das könnte ...").
- Das Sensitivitätsmodell ist eine historische Daumenregel, keine Prognose. Formuliere
  entsprechend ("historisch reagierten Banken auf ... typischerweise mit ...").
- Kein Markdown, keine Aufzählungszeichen, keine Tabellen, keine Abkürzungen, die man
  schlecht vorlesen kann. Schreibe Zahlen sprechbar ("minus eins Komma zwei Prozent",
  "zwölf Basispunkte"). Tickersymbole durch Firmennamen ersetzen.
- Kurze Sätze, natürlicher Sprechrhythmus, keine Floskeln, kein Disclaimer-Gerede.
- Länge: etwa {config.SCRIPT_TARGET_MINUTES} Minuten Sprechzeit (ca. {config.SCRIPT_TARGET_MINUTES * 140} Wörter).

AUFBAU
1. Einstieg: ein Satz mit Datum und dem wichtigsten Thema des Tages.
2. Asien über Nacht: Indizes, Yen, Yuan, China-Signale.
3. USA: Vortagesschluss und aktuelle Futures.
4. Zinsen und Inflation: US-Renditen, Bund-Future, relevante Notenbank-News.
5. Rohstoffe und Devisen: Öl, Gas, Metalle, Euro.
6. Earnings seit gestern: wer berichtet hat, Überraschung, Kursreaktion. Dann die
   ÜBERGREIFENDEN THEMEN: Was sagen mehrere Berichte gemeinsam (Nachfrage, Preise,
   Margen, Zölle, KI-Investitionen, China ...)? Liegen Transkript-Auszüge vor, nutze
   vor allem die Aussagen des Managements im Q&A.
7. Was heißt das heute für Europa: Sektoren mit Rückenwind und Gegenwind, gestützt auf
   die Daten und das Sensitivitätsmodell. Konkret und mit Begründung.
8. Ein Satz zum Mitnehmen.

Gib danach eine Zeile "===SHOWNOTES===" aus und darunter 5 bis 8 knappe Stichpunkte
(Textform, mit Zahlen) als Notiz zum Nachlesen."""


def build_payload(date_str: str, markets: dict, news: list, earnings: list, sens: dict) -> str:
    payload = {
        "datum": date_str,
        "maerkte": markets,
        "sensitivitaetsmodell": sens,
        "earnings_seit_gestern": earnings,
        "nachrichten": news,
    }
    return json.dumps(payload, ensure_ascii=False, indent=1, default=str)


def split_output(text: str) -> tuple[str, str]:
    if "===SHOWNOTES===" in text:
        script, notes = text.split("===SHOWNOTES===", 1)
        return script.strip(), notes.strip()
    return text.strip(), ""


def write(date_str: str, markets: dict, news: list, earnings: list, sens: dict) -> tuple[str, str]:
    import anthropic

    client = anthropic.Anthropic()  # liest ANTHROPIC_API_KEY aus der Umgebung
    payload = build_payload(date_str, markets, news, earnings, sens)
    # Das Modell denkt standardmäßig (adaptiv) vor dem Schreiben; Denk-Tokens
    # zählen gegen max_tokens. Daher großzügiges Limit und mittlere Effort-Stufe.
    msg = client.messages.create(
        model=config.LLM_MODEL,
        max_tokens=config.LLM_MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Daten für das heutige Briefing:\n\n{payload}"}],
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

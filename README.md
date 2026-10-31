# Morning Briefing – Makro & Europa als privater Podcast

Jeden Werktag gegen 6:45 Uhr sammelt die Pipeline Daten zu Asien über Nacht,
US-Vortag, Zinsen, Rohstoffen, Devisen und Earnings, schätzt die historische
Reaktion europäischer Sektoren darauf, lässt ein Sprachmodell ein Skript
schreiben, vertont es lokal und stellt die Folge in einen Podcast-Feed.

```
yfinance / RSS / Earnings ─┐
Sensitivitätsmodell ───────┼─> Skript (Claude API) ─> Piper (lokal) ─> MP3 ─> feed.xml (GitHub Pages)
                           └─> archive/JJJJ-MM-TT/data.json + script.txt
```

## Einrichtung (einmalig, ca. 20 Minuten)

1. **Repository anlegen**: neues GitHub-Repo, Inhalt dieses Ordners hochladen.
   *Öffentliches Repo* = unbegrenzte Actions-Minuten und GitHub Pages gratis.
   Der Feed ist dann technisch öffentlich erreichbar (nicht gelistet). Enthalten
   sind nur öffentliche Marktinfos – keine Positionen eintragen.
   *Privates Repo* geht auch (2.000 Freiminuten/Monat reichen), Pages für private
   Repos braucht aber einen bezahlten Plan.
2. **API-Key** unter *Settings → Secrets and variables → Actions → Secrets*:
   - `ANTHROPIC_API_KEY` (Pflicht, console.anthropic.com)
   - `API_NINJAS_KEY` (optional, Gratis-Key für US-Call-Transkripte)
3. **Variablen** unter demselben Menü, Reiter *Variables*:
   - `FEED_BASE_URL` = `https://<dein-github-name>.github.io/<repo-name>`
   - `FEED_SECRET_PATH` = beliebige Zeichenkette, z. B. `mb-7f3k9q`
4. **Erster Lauf**: *Actions → Morning Briefing → Run workflow*. Danach unter
   *Settings → Pages* als Quelle den Branch `gh-pages` wählen.
5. **Abonnieren**: In der Podcast-App „Feed per URL hinzufügen“:
   `FEED_BASE_URL/FEED_SECRET_PATH/feed.xml`
   (Apple Podcasts: Mediathek → „Sendung per URL folgen“; Overcast / Pocket Casts
   können das ebenfalls.)

## Beim ersten Lauf prüfen

Im Log von *Briefing erzeugen* stehen Warnungen wie `Keine Daten für: …` oder
`Feed … lieferte keine Einträge`. Betroffene Ticker oder Feeds in
`briefing/config.py` anpassen. Vor allem die Sektor-ETF-Ticker (`EU_SECTORS`)
und TTF-Gas sollte man einmal verifizieren.

## Lokal testen

```bash
pip install -r requirements.txt pytest
pytest -q                                   # Offline-Tests
python -m briefing.main --force --dry-run   # nur Daten -> archive/…/data.json
```

Für einen kompletten lokalen Lauf zusätzlich `ffmpeg` installieren und die
Stimme nach `voices/` laden (URLs im Workflow).

## Anpassen

| Was | Wo |
|---|---|
| Märkte, Sektoren, Earnings-Universum, News-Feeds | `briefing/config.py` |
| Aufbau, Ton, Länge des Briefings | `SYSTEM_PROMPT` in `briefing/script_writer.py` |
| Faktoren des Sensitivitätsmodells | `SENS_FACTORS` in `config.py` |
| Andere Transkript-Quelle | `fetch_transcript()` in `briefing/earnings.py` |
| Andere Stimme | `PIPER_VOICE` (z. B. `de_DE-thorsten-medium`, schneller) |

## Grenzen

- Yahoo-Finance-Daten sind inoffiziell und manchmal lückenhaft; Bund-Rendite
  wird über den Bund-Future angenähert.
- Das Sensitivitätsmodell nutzt Tagesschlusskurse. Es ist eine historische
  Daumenregel, keine Eröffnungsprognose.
- Gratis-Transkripte gibt es kaum für europäische Werte.
- Nur öffentliche Quellen verwenden – keine Bloomberg-Terminal-Inhalte.
- Kosten: GitHub und Vertonung gratis, Sprachmodell grob 1–3 € im Monat.

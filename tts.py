"""Lokale, kostenlose Vertonung mit Piper (läuft auf CPU) + MP3 per ffmpeg."""
from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from . import config

log = logging.getLogger(__name__)


def _prepare(text: str) -> str:
    # Absätze -> kleine Pausen, Reste von Markdown entfernen
    text = re.sub(r"[*#_`>|]", "", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    return text.strip()


def synthesize(text: str, out_mp3: Path) -> float:
    """Erzeugt die MP3 und gibt die Dauer in Sekunden zurück."""
    voice = Path(config.PIPER_VOICE_DIR) / f"{config.PIPER_VOICE}.onnx"
    if not voice.exists():
        raise FileNotFoundError(f"Piper-Stimme fehlt: {voice} (siehe README)")
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "briefing.wav"
        subprocess.run(
            [sys.executable, "-m", "piper", "--model", str(voice),
             "--output_file", str(wav)],
            input=_prepare(text).encode("utf-8"), check=True,
        )
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
             "-ac", "1", "-codec:a", "libmp3lame", "-b:a", "64k", str(out_mp3)],
            check=True,
        )
    return duration(out_mp3)


def duration(path: Path) -> float:
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(res.stdout)["format"]["duration"])

"""Lokale, kostenlose Vertonung + MP3 per ffmpeg.

Standard ist Kokoro (natürlicher, nur Englisch u. a., kein Deutsch).
Piper bleibt als Alternative (kann Deutsch), umschaltbar über TTS_ENGINE.
"""
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
    text = re.sub(r"[*#_`>|]", "", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    return text.strip()


def paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", _prepare(text)) if p.strip()]


def voice_style(kokoro, mix: dict[str, float]):
    """Gewichteter Mix mehrerer Kokoro-Stimmen (Gewichte werden normiert)."""
    total = sum(mix.values())
    return sum(kokoro.get_voice_style(v) * (w / total) for v, w in mix.items())


def _kokoro_wav(text: str, wav: Path) -> None:
    import numpy as np
    import soundfile as sf
    from kokoro_onnx import Kokoro

    model_dir = Path(config.KOKORO_MODEL_DIR)
    k = Kokoro(str(model_dir / "kokoro-v1.0.onnx"), str(model_dir / "voices-v1.0.bin"))
    style = voice_style(k, config.KOKORO_VOICE_MIX)
    chunks, sr = [], 24000
    for para in paragraphs(text):
        samples, sr = k.create(para, voice=style, speed=config.TTS_SPEED, lang=config.KOKORO_LANG)
        chunks.append(samples)
        chunks.append(np.zeros(int(sr * config.PARAGRAPH_PAUSE_S), dtype=samples.dtype))
    sf.write(str(wav), np.concatenate(chunks), sr)


def _piper_wav(text: str, wav: Path) -> None:
    voice = Path(config.PIPER_VOICE_DIR) / f"{config.PIPER_VOICE}.onnx"
    if not voice.exists():
        raise FileNotFoundError(f"Piper-Stimme fehlt: {voice} (siehe README)")
    subprocess.run(
        [sys.executable, "-m", "piper", "--model", str(voice), "--output_file", str(wav)],
        input=_prepare(text).encode("utf-8"), check=True,
    )


def pitch_filter(sr: int = 24000) -> list[str]:
    """Tonhöhe verschieben, ohne das Tempo zu ändern (ffmpeg asetrate + atempo)."""
    p = config.TTS_PITCH
    if abs(p - 1.0) < 1e-3:
        return []
    return ["-af", f"asetrate={sr}*{p},aresample={sr},atempo={1 / p:.4f}"]


def synthesize(text: str, out_mp3: Path) -> float:
    """Erzeugt die MP3 und gibt die Dauer in Sekunden zurück."""
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "briefing.wav"
        if config.TTS_ENGINE == "piper":
            _piper_wav(text, wav)
        else:
            _kokoro_wav(text, wav)
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), *pitch_filter(),
             "-ac", "1", "-codec:a", "libmp3lame", "-b:a", "96k", str(out_mp3)],
            check=True,
        )
    return duration(out_mp3)


def duration(path: Path) -> float:
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(res.stdout)["format"]["duration"])

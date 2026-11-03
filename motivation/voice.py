"""Offline male narration via a public-domain-trained Piper voice; eSpeak safety fallback.

The John (medium) Piper model card identifies LibriVox public-domain recordings.
Model files are downloaded to local cache, never stored in Git.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import wave
from pathlib import Path

from .common import PipelineError, download, duration, tool

MODEL_ID = "en_US-john-medium"
MODEL_ROOT = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/john/medium/"
VOICE_CREDIT = "Piper en_US-john-medium (LibriVox public-domain dataset; model from rhasspy/piper-voices)"


def voice_engine() -> str:
    """Prefer offline neural voice where installed; explicit 'espeak' selects diagnostic voice."""
    return os.environ.get("MOTIVATION_VOICE", "piper").strip().lower()


def _piper_model() -> Path:
    root = Path(os.environ.get("PIPER_MODEL_DIR", ".cache/piper")).resolve()
    model = root / (MODEL_ID + ".onnx")
    config = root / (MODEL_ID + ".onnx.json")
    if not model.exists() or model.stat().st_size < 10_000_000:
        download(MODEL_ROOT + model.name, model, max_mb=70)
    if not config.exists() or config.stat().st_size < 100:
        download(MODEL_ROOT + config.name, config, max_mb=1)
    return model


def synthesize_sentences(sentences: list[str], directory: Path) -> dict:
    """Return paths and engine; fail instead of silently shipping a robot voice unless opted-in."""
    directory.mkdir(parents=True, exist_ok=True)
    requested = voice_engine()
    outputs = []
    label = ""
    if requested == "piper":
        try:
            from piper.voice import PiperVoice
            model = _piper_model()
            voice = PiperVoice.load(str(model), use_cuda=False)
            for i, sentence in enumerate(sentences):
                path = directory / f"line_{i:02}.wav"
                with wave.open(str(path), "wb") as wav:
                    voice.synthesize_wav(sentence, wav)
                if duration(path) < 0.25:
                    raise PipelineError("Piper output too short")
                outputs.append(path)
            label = VOICE_CREDIT
        except Exception as exc:
            if os.environ.get("ALLOW_ROBOTIC_VOICE", "0") != "1":
                raise PipelineError(f"Neural narration unavailable: {exc}. Set ALLOW_ROBOTIC_VOICE=1 only for diagnostic videos") from exc
            outputs.clear()
            requested = "espeak"
    if requested == "espeak":
        engine = shutil.which("espeak-ng") or shutil.which("espeak")
        if not engine:
            raise PipelineError("eSpeak unavailable")
        for i, sentence in enumerate(sentences):
            path = directory / f"line_{i:02}.wav"
            subprocess.run([engine, "-v", "en", "-s", "142", "-w", str(path), sentence],
                           capture_output=True, check=True)
            outputs.append(path)
        label = "diagnostic eSpeak narration (robotic)"
    if len(outputs) != len(sentences):
        raise PipelineError("Narration output count mismatch")
    return {"paths": outputs, "engine": label}

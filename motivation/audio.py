"""Locally synthesized ORIGINAL instrumental bed, plus optional Demucs cleanup."""
from __future__ import annotations
import math
import subprocess
import wave
from pathlib import Path

import numpy as np
from .common import PipelineError, tool

MOODS = {
    "determined": ([110.0, 130.81, 164.81], 0.15),
    "hopeful": ([130.81, 164.81, 196.00], 0.12),
    "calm": ([110.0, 146.83, 174.61], 0.10),
    "intense": ([98.00, 116.54, 146.83], 0.17),
}


def make_music(path: Path, seconds: float, mood: str = "determined") -> Path:
    """Gentle sustained synth chords; self-generated so no third-party music license needed."""
    sample_rate = 22050
    voices, amp = MOODS.get(mood, MOODS["determined"])
    total = max(1, int(seconds * sample_rate))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        step = sample_rate * 3
        for offset in range(0, total, step):
            count = min(step, total - offset)
            t = (np.arange(offset, offset+count, dtype=np.float64)) / sample_rate
            shape = (1 - np.exp(-np.mod(t, 8.0)*.8)) * np.minimum(1, (seconds - t) / 2.0)
            wave_data = np.zeros(count, dtype=np.float64)
            for j, freq in enumerate(voices):
                wave_data += np.sin(2*np.pi*freq*t + 0.15*np.sin(2*np.pi*0.13*t+j)) / (j+2)
                wave_data += 0.12*np.sin(2*np.pi*(freq/2)*t) / (j+2)
            # Low-level arpeggio adds pulse to otherwise sustained chords.
            melody_freq = np.asarray(voices)[(np.floor(t / 2).astype(int)) % len(voices)]*2
            melody = 0.075*np.sin(2*np.pi*melody_freq*t)
            out = np.clip((wave_data+melody)*shape*amp, -1.0, 1.0)
            w.writeframes((out*32767).astype("<i2").tobytes())
    return path


def demucs_vocals(path: Path, output: Path) -> Path:
    """Optional, heavyweight local separation. Never claims perfect removal."""
    import importlib.util
    if importlib.util.find_spec("demucs") is None:
        raise PipelineError("Demucs is not installed. Install optional demucs to try separating music.")
    subprocess.run(["python", "-m", "demucs", "--two-stems=vocals", "-o", str(output), str(path)], check=True)
    results = list(output.glob("**/vocals.wav"))
    if not results:
        raise PipelineError("Demucs did not produce a vocal track")
    return results[0]

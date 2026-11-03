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
    """Compose a royalty-free cinematic bed with a chord progression, pulse, and swells.

    Streaming synthesis caps RAM regardless of duration. This is original audio,
    not a third-party song or imitation of an existing copyrighted composition.
    """
    import numpy as np
    sr = 22050
    length = max(1.0, float(seconds))
    progressions = {
        "determined": [(110, 130.81, 164.81), (98, 123.47, 146.83), (87.31, 110, 130.81), (98, 123.47, 164.81)],
        "hopeful": [(130.81, 164.81, 196), (146.83, 174.61, 220), (164.81, 196, 246.94), (146.83, 196, 220)],
        "calm": [(110, 146.83, 174.61), (98, 130.81, 164.81), (87.31, 130.81, 174.61), (98, 146.83, 196)],
        "intense": [(98, 116.54, 146.83), (87.31, 110, 130.81), (82.41, 98, 123.47), (98, 123.47, 146.83)]
    }
    chords = progressions.get(mood, progressions["determined"])
    bpm = 96 if mood == "calm" else 108 if mood == "hopeful" else 116
    beat = 60 / bpm
    total = int(length * sr)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(sr)
        rng = np.random.default_rng(4096)
        for offset in range(0, total, sr * 3):
            t = np.arange(offset, min(total, offset+sr*3), dtype=np.float64) / sr
            chord_idx = np.floor(t / (beat * 8)).astype(int) % len(chords)
            phase_in_beat = np.mod(t, beat)
            y = np.zeros(len(t), dtype=np.float64)
            for k, chord in enumerate(chords):
                mask = chord_idx == k
                if not mask.any():
                    continue
                tm = t[mask]
                pad = sum(np.sin(2*np.pi*f*tm + .2*np.sin(2*np.pi*.09*tm+j)) / (j+2)
                          for j, f in enumerate(chord))
                bass = np.sin(2*np.pi*(chord[0]/2)*tm) * .27
                y[mask] = .22*pad + .18*bass
            # Original low-frequency kick, soft snare, and a periodic rising swell.
            kick = .20*np.sin(2*np.pi*(53 - 23*np.minimum(phase_in_beat, .18)/.18)*t) * np.exp(-26*phase_in_beat)
            snare_phase = np.mod(t + beat, beat*2)
            snare = .07*rng.standard_normal(len(t)) * np.exp(-34*snare_phase)
            shimmer = .028*np.sin(2*np.pi*440*t) * np.sin(np.pi*np.mod(t,beat*8)/(beat*8))**4
            fade_in = np.minimum(1, t / 2.0)
            fade_out = np.minimum(1, np.maximum(0, length - t) / 2.0)
            y = np.tanh((y + kick + snare + shimmer) * fade_in * fade_out * 1.2)
            wav.writeframes((np.clip(y, -.97, .97) * 32767).astype('<i2').tobytes())
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

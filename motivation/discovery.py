"""Rank multiple licensed-recording candidates without silently clearing copyright or music."""
from __future__ import annotations
import importlib.util
from pathlib import Path
from .analysis import gemini_selection, music_check, transcribe
from .audio import demucs_vocals
from .common import PipelineError
from .sources import licensed_audio


def select_archive_recording(query: str, directory: Path, *, separate_music: bool = False,
                             allow_unknown_music: bool = False, clean_confirmed: bool = False,
                             max_candidates: int = 3) -> dict:
    if not importlib.util.find_spec("inaSpeechSegmenter") and not (allow_unknown_music or clean_confirmed or separate_music):
        raise PipelineError("Music classifier is not installed. Install inaSpeechSegmenter before using Archive speech")
    directory.mkdir(parents=True, exist_ok=True)
    excluded = set()
    candidates = []
    for i in range(max_candidates):
        try:
            result = licensed_audio(query, directory / f"candidate_{i}", exclude=excluded)
            excluded.add(result["identifier"])
            audio = Path(result["path"])
            check = music_check(audio)
            if separate_music and check["status"] != "likely_clean":
                audio = demucs_vocals(audio, directory / f"demucs_{i}")
                check = music_check(audio)
                check["note"] = "Separated vocals are not automatically music-free; human listening required"
            if check["status"] != "likely_clean" and not (clean_confirmed or allow_unknown_music):
                continue
            cues = transcribe(audio)
            if not cues:
                continue
            selection = gemini_selection(cues)
            candidates.append({"path": audio, "source": result, "music_check": check,
                               "cues": cues, "selection": selection,
                               "quality_score": float(selection.get("score", 0))})
        except (PipelineError, ValueError, OSError) as exc:
            continue
    if not candidates:
        raise PipelineError("No confidently clean, intelligible, licensed-source speech in sampled Archive results; use original voice or provide approved audio")
    candidates.sort(key=lambda x: x["quality_score"], reverse=True)
    return candidates[0]

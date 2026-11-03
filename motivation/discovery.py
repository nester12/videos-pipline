"""Rank multiple licensed-recording candidates without silently clearing copyright or music."""
from __future__ import annotations
from pathlib import Path
from .analysis import gemini_selection, music_check, transcribe
from .audio import demucs_vocals
from .common import PipelineError
from .sources import licensed_audio


def select_archive_recording(query: str, directory: Path, *, separate_music: bool = False,
                             allow_unknown_music: bool = False, clean_confirmed: bool = False,
                             max_candidates: int = 3) -> dict:
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
            if check["status"] != "likely_clean":
                check["soundtrack_policy"] = "Preserve source audio: do NOT layer extra soundtrack until music is reviewed"
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
        raise PipelineError("No intelligible Archive recording with a suitable uploader-asserted licence in sampled results. Try a more specific topic or supply your own licensed video.")
    candidates.sort(key=lambda x: x["quality_score"], reverse=True)
    return candidates[0]

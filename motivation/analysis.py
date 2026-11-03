"""Speech transcription, selection, and conservative music checks."""
from __future__ import annotations
import json
import os
import re
import subprocess
from pathlib import Path
import requests
from .common import PipelineError, duration, tool

_CACHED_MODEL = None


def gemini_model() -> str:
    """Choose an actually available Flash/Lite model. GEMINI_MODEL overrides this."""
    global _CACHED_MODEL
    explicit = os.getenv("GEMINI_MODEL")
    if explicit:
        if not re.fullmatch(r"gemini-[a-zA-Z0-9.-]+", explicit):
            raise PipelineError("Invalid GEMINI_MODEL identifier")
        return explicit
    if _CACHED_MODEL:
        return _CACHED_MODEL
    preferred = ("gemini-3.5-flash-lite", "gemini-3-flash", "gemini-2.5-flash-lite", "gemini-2.5-flash")
    available = set()
    key = os.getenv("GEMINI_API_KEY")
    if key:
        try:
            r = requests.get("https://generativelanguage.googleapis.com/v1beta/models",
                             headers={"x-goog-api-key": key}, params={"pageSize": 100}, timeout=18)
            r.raise_for_status()
            available = {m["name"].split("/")[-1] for m in r.json().get("models", [])
                         if "generateContent" in m.get("supportedGenerationMethods", [])}
        except (KeyError, ValueError, requests.RequestException):
            pass
    _CACHED_MODEL = next((m for m in preferred if m in available), "gemini-2.5-flash")
    return _CACHED_MODEL


def gemini_endpoint() -> str:
    return "https://generativelanguage.googleapis.com/v1beta/models/" + gemini_model() + ":generateContent"


def transcribe(audio: Path, model_size="tiny") -> list[dict]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise PipelineError("Install requirements.txt to transcribe externally sourced audio") from exc
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(audio), vad_filter=True, beam_size=2, word_timestamps=True)
    cues = []
    for seg in segments:
        if seg.words:
            group = []
            for word in seg.words:
                group.append(word)
                if len(group) >= 5 or str(word.word).strip().endswith((".", "?", "!", ",")):
                    cues.append({"start": float(group[0].start), "end": float(group[-1].end),
                                 "text": "".join(w.word for w in group).strip()})
                    group = []
            if group:
                cues.append({"start": float(group[0].start), "end": float(group[-1].end),
                             "text": "".join(w.word for w in group).strip()})
        else:
            cues.append({"start": float(seg.start), "end": float(seg.end), "text": seg.text.strip()})
    return [c for c in cues if c["end"] > c["start"] and c["text"]]


def music_check(audio: Path) -> dict:
    """Optional local classifier. Unavailable model => unknown, never falsely claim clean."""
    try:
        from inaSpeechSegmenter import Segmenter
    except ImportError:
        return {"status": "unknown", "reason": "Optional inaSpeechSegmenter model is not installed; do not assume speech-only"}
    segments = Segmenter(vad_engine="smn", detect_gender=False)(str(audio))
    spans = {"music": 0.0, "speech": 0.0, "noise": 0.0}
    for label, start, end in segments:
        category = "music" if label == "music" else "speech" if label in ("male", "female", "speech") else "noise"
        spans[category] += float(end) - float(start)
    total = max(1, sum(spans.values()))
    ratio = spans["music"] / total
    return {"status": "music_detected" if ratio > .12 else "likely_clean", "music_ratio": round(ratio, 3),
            "warning": "Overlapping quiet music may go undetected; review audio before publishing"}


def gemini_selection(cues: list[dict]) -> dict:
    """Use model to suggest an emotionally complete excerpt; conservative local fallback."""
    transcript = "\n".join(f'{c["start"]:.1f}-{c["end"]:.1f}: {c["text"]}' for c in cues[:200])
    from .quality import best_window
    fallback = best_window(cues)
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return fallback
    prompt = ("You are a motivational short-form editor. Select an impactful, coherent contiguous section of the transcript. "
              "Choose natural length based on hook and payoff, never artificially extend. Avoid taking words out of context. "
              "Respond ONLY JSON: start (seconds), end (seconds), mood (one of determined, hopeful, calm, intense), "
              "visual_query (brief Pexels footage query), score (1-10), reason (short). The selected interval must be within timestamps.\n" + transcript)
    url = gemini_endpoint()
    try:
        r = requests.post(url, params={"key": key}, json={"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": .25}}, timeout=45)
        r.raise_for_status()
        raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(raw)
        start = max(float(cues[0]["start"]), float(result["start"]))
        end = min(float(cues[-1]["end"]), float(result["end"]))
        if end - start < 12 or not (start < end):
            return fallback
        return {"start": start, "end": end,
                "mood": result.get("mood", "determined") if result.get("mood") in ("determined", "hopeful", "calm", "intense") else "determined",
                "visual_query": str(result.get("visual_query", "athlete running"))[:80],
                "score": max(1, min(10, int(result.get("score", 6)))), "reason": str(result.get("reason", ""))[:240]}
    except (ValueError, TypeError, KeyError, IndexError, requests.RequestException):
        return fallback


def slice_audio(audio: Path, result: Path, start: float, end: float) -> None:
    if end <= start:
        raise PipelineError("Invalid speech selection")
    subprocess.run([tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-ss", str(start), "-i", str(audio),
                    "-t", str(end-start), "-ac", "1", "-ar", "44100", str(result)], check=True)


def shift_cues(cues: list[dict], start: float, end: float) -> list[dict]:
    return [{"start": max(0, c["start"] - start), "end": min(end, c["end"]) - start,
             "text": c["text"]} for c in cues if c["end"] > start and c["start"] < end and c["text"]]

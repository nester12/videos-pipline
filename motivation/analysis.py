"""Speech transcription, selection, and conservative music checks."""
from __future__ import annotations
import json
import os
import re
import subprocess
from pathlib import Path
import requests
from .common import PipelineError, duration, tool

MOTIVATIONAL_SCRIPT = [
    "The person you become is decided by what you do when nobody is watching.",
    "Start before you feel ready. Take the first step even when it feels uncomfortable.",
    "Discipline is showing up on the ordinary days, when motivation has disappeared.",
    "When you fall behind, do not quit. Learn something, adjust your direction, and begin again.",
    "Progress is not always loud. Sometimes it is one difficult choice made consistently.",
    "You are building the strength to finish what you started. Keep going.",
]


def original_narration(directory: Path, script: list[str] | None = None) -> dict:
    """Generate royalty-free prototype narration with locally installed eSpeak."""
    import shutil
    directory.mkdir(parents=True, exist_ok=True)
    script = script or MOTIVATIONAL_SCRIPT
    engine = shutil.which("espeak-ng") or shutil.which("espeak")
    if not engine:
        raise PipelineError("eSpeak is required for no-key synthetic narration")
    paths, cues = [], []
    elapsed = 0.0
    for i, phrase in enumerate(script):
        path = directory / f"line_{i:02}.wav"
        subprocess.run([engine, "-v", "en", "-s", "142", "-w", str(path), phrase], check=True, capture_output=True)
        d = duration(path)
        paths.append(path)
        words = phrase.split()
        # eSpeak creates one WAV per sentence; split into short caption chunks.
        chunks = [words[j:j+4] for j in range(0, len(words), 4)]
        weights = [sum(len(w) for w in chunk) for chunk in chunks]
        total_weight = max(1, sum(weights))
        prior = 0
        for chunk, weight in zip(chunks, weights):
            cues.append({"start": round(elapsed + d * prior / total_weight, 2),
                         "end": round(elapsed + d * (prior + weight) / total_weight, 2),
                         "text": " ".join(chunk)})
            prior += weight
        elapsed += d
    # concat wav by demuxer and normalize before rendering
    lst = directory / "narration_files.txt"
    lst.write_text("\n".join("file '" + p.name + "'" for p in paths), encoding="utf-8")
    merged = directory / "narration.wav"
    subprocess.run([tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-ac", "1", "-ar", "22050", str(merged)], check=True)
    return {"path": merged, "cues": cues, "duration": elapsed, "script": " ".join(script), "origin": "original royalty-free prototype speech"}


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
    fallback = {"start": cues[0]["start"], "end": cues[-1]["end"], "mood": "determined",
                "visual_query": "athlete running outdoors", "score": 6, "reason": "fallback: use complete available speech"}
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return fallback
    prompt = ("You are a motivational short-form editor. Select an impactful, coherent contiguous section of the transcript. "
              "Choose natural length based on hook and payoff, never artificially extend. Avoid taking words out of context. "
              "Respond ONLY JSON: start (seconds), end (seconds), mood (one of determined, hopeful, calm, intense), "
              "visual_query (brief Pexels footage query), score (1-10), reason (short). The selected interval must be within timestamps.\n" + transcript)
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
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


def gemini_original_script(topic: str = "discipline") -> list[str] | None:
    """Original fallback writing, not copied quotations. Returns None on free API errors."""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    prompt = ("Write an entirely ORIGINAL motivational voiceover for short-form video on the theme "
              + repr(topic[:65]) + ". Start with a distinctive emotional hook. "
              "Write 6 to 9 short punchy sentences totaling about 100-150 words. "
              "Make a complete arc, with a satisfying final sentence. Avoid quoting existing speeches or famous people. "
              "Return only JSON object {\"sentences\": [\"...\"]}.")
    try:
        r = requests.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
             params={"key": key}, json={"contents": [{"parts": [{"text": prompt}]}],
                                     "generationConfig": {"responseMimeType": "application/json", "temperature": .8}}, timeout=45)
        r.raise_for_status()
        generated = json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
        items = generated.get("sentences", [])
        if isinstance(items, list) and 4 <= len(items) <= 12 and sum(len(s.split()) for s in items) >= 55:
            return [str(s)[:240] for s in items]
    except (ValueError, TypeError, KeyError, IndexError, requests.RequestException):
        pass
    return None

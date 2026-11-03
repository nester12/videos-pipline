"""Local, deterministic selection of a complete spoken thought; Gemini can refine it."""
from __future__ import annotations
import re

HOOK_WORDS = ("never", "stop", "today", "tomorrow", "discipline", "dream", "remember", "start",
              "listen", "imagine", "failure", "strength", "courage", "choice", "life")
CLOSING_WORDS = ("again", "now", "today", "going", "forward", "begin", "start", "stronger", "ready")


def candidate_windows(cues: list[dict], *, min_seconds: float = 20, max_seconds: float = 105) -> list[dict]:
    if not cues:
        return []
    ordered = sorted((dict(c) for c in cues if c.get("text") and float(c["end"]) > float(c["start"])),
                     key=lambda c: float(c["start"]))
    if not ordered:
        return []
    boundaries = [i for i, cue in enumerate(ordered) if
                  i == len(ordered) - 1 or re.search(r"[.!?][\"']?$", str(cue["text"]).strip())]
    starts = [0] + [i+1 for i in boundaries if i+1 < len(ordered)]
    candidates = []
    for a in starts:
        for b in boundaries:
            if b < a:
                continue
            start, end = float(ordered[a]["start"]), float(ordered[b]["end"])
            seconds = end - start
            if seconds < min_seconds and not (a == 0 and b == len(ordered) - 1):
                continue
            if seconds > max_seconds:
                break
            text = " ".join(str(c["text"]).strip() for c in ordered[a:b+1])
            words = re.findall(r"[A-Za-z']+", text.lower())
            if len(words) < 18:
                continue
            first = " ".join(words[:20]); last = " ".join(words[-15:])
            wpm = 60 * len(words) / max(1, seconds)
            score = 5.0
            score += 1.3 if any(w in first.split() for w in HOOK_WORDS) else 0
            score += 0.9 if any(w in last.split() for w in CLOSING_WORDS) else 0
            score += 0.6 if 35 <= seconds <= 85 else 0
            score += 0.4 if 90 <= wpm <= 210 else -0.3
            score += 0.3 * min(1, len(set(words)) / len(words) / 0.5)
            score -= min(2, sum(words.count(w) for w in ("um", "uh", "erm")) * 0.4)
            candidates.append({"start": start, "end": end, "score": round(score, 3),
                               "words": len(words), "excerpt": text[:300]})
    if not candidates:
        return [{"start": float(ordered[0]["start"]), "end": float(ordered[-1]["end"]),
                 "score": 4.0, "words": 0, "excerpt": " ".join(c["text"] for c in ordered)[:300]}]
    return sorted(candidates, key=lambda c: c["score"], reverse=True)[:12]


def best_window(cues: list[dict]) -> dict:
    candidates = candidate_windows(cues)
    if not candidates:
        raise ValueError("No speech transcript for selection")
    c = candidates[0]
    return {"start": c["start"], "end": c["end"], "mood": "determined",
            "visual_query": "runner training outdoors", "score": min(10, round(c["score"])),
            "reason": "Highest-ranked locally scored complete speech passage"}

"""Pexels primary, Pixabay backup, copyright-free procedural visual fallback."""
from __future__ import annotations
import math
import os
from pathlib import Path
import requests
from .common import PipelineError, download, run, tool


def relevance_score(title: str, query: str) -> int:
    """Prefer genuinely relevant actions over loosely related stock videos."""
    import re
    words = set(re.findall(r"[a-z]{3,}", query.lower()))
    title_words = set(re.findall(r"[a-z]{3,}", title.lower()))
    value = 3 * len(words & title_words)
    query_text = query.lower()
    if any(x in query_text for x in ("gym", "training", "athlete", "workout")):
        value += 2 * len(title_words & {"exercise", "fitness", "lifting", "weights", "weightlifting",
                                         "squat", "sprinting", "trainer", "training", "workout"})
        value -= 4 * len(title_words & {"massage", "massaging", "treatment", "relaxation", "office"})
    if "runner" in query_text:
        value += 3 * len(title_words & {"running", "runner", "jogging", "sprint", "sprinting"})
    return value


def pexels(query: str, folder: Path):
    key = os.getenv("PEXELS_API_KEY")
    if not key:
        return None
    response = requests.get("https://api.pexels.com/v1/videos/search", headers={"Authorization": key},
            params={"query": query, "orientation": "portrait", "per_page": 14}, timeout=30)
    response.raise_for_status()
    videos = response.json().get("videos", [])
    videos.sort(key=lambda x: relevance_score(x.get("url", "").replace("-", " "), query), reverse=True)
    for item in videos:
        if relevance_score(item.get("url", "").replace("-", " "), query) <= 0:
            continue
        files = [f for f in item.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("link")]
        files.sort(key=lambda f: abs((f.get("width") or 720) - 720) + abs((f.get("height") or 1280) - 1280))
        for f in files[:2]:
            try:
                path = download(f["link"], folder / "background.mp4", max_mb=70)
                return {"path": path, "source": item.get("url", "https://www.pexels.com"),
                        "credit": item.get("user", {}).get("name", "Pexels contributor")}
            except (requests.RequestException, PipelineError):
                continue
    return None


def pixabay(query: str, folder: Path):
    key = os.getenv("PIXABAY_API_KEY")
    if not key:
        return None
    response = requests.get("https://pixabay.com/api/videos/", params={"key": key, "q": query, "per_page": 5}, timeout=30)
    response.raise_for_status()
    hits = response.json().get("hits", [])
    hits.sort(key=lambda x: relevance_score(x.get("tags", ""), query), reverse=True)
    for item in hits:
        if relevance_score(item.get("tags", ""), query) <= 0:
            continue
        options = item.get("videos", {})
        for size in ("medium", "small", "large", "tiny"):
            video = options.get(size, {})
            if video.get("url"):
                try:
                    path = download(video["url"], folder / "background.mp4", max_mb=70)
                    return {"path": path, "source": item.get("pageURL", "https://pixabay.com"),
                            "credit": item.get("user", "Pixabay contributor")}
                except (requests.RequestException, PipelineError):
                    continue
    return None


def get_background(query: str, folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    for provider in (pexels, pixabay):
        try:
            result = provider(query, folder)
            if result:
                return result
        except requests.RequestException:
            pass
    return None


def procedural_background(output: Path, seconds: float, width=720, height=1280):
    """Original animated monochrome shapes. Offline fallback, no media licensing required."""
    output.parent.mkdir(parents=True, exist_ok=True)
    frames = max(1, int(math.ceil(seconds * 24)))
    expression = ("color=c=#161616:s=" + str(width) + "x" + str(height) + ":r=24,"
       "drawbox=x=iw/2-180:y=ih/3:w=360:h=540:color=#303030@0.7:t=fill,"
       "drawbox=x=80:y=ih*0.7:w=560:h=18:color=#555555@0.7:t=fill,"
       "drawbox=x=iw*0.12:y=ih*0.08:w=8:h=ih*0.84:color=#6f6f6f@0.7:t=fill")
    run([tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", expression,
         "-frames:v", str(frames), "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(output)])
    return {"path": output, "source": "original procedural background", "credit": "original"}

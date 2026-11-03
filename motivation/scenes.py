"""Assemble distinct rights-sourced visual scenes with precise cuts."""
from __future__ import annotations
import math
from pathlib import Path
from .backgrounds import get_background, procedural_background
from .common import run, tool


def montage(visual_query: str, folder: Path, seconds: float, *, offline: bool = False, preview: bool = False) -> dict:
    """Build a continuously playing 9:16 montage and source attribution records.

    Each source video is locally transcoded to the same FPS/resolution/audio-free
    format before concat. This avoids concat failures from mixed source formats.
    """
    folder.mkdir(parents=True, exist_ok=True)
    total = max(1.0, float(seconds))
    n = 1 if preview else min(5, max(2, math.ceil(total / 18)))
    search_terms = [visual_query, "gym athlete training", "runner sprinting outdoors",
                    "dramatic mountain clouds", "silhouette workout sunset"]
    paths = []
    sources = []
    for i in range(n):
        clip_len = total / n if i < n - 1 else total - (total / n) * (n - 1)
        scene_dir = folder / f"scene_{i+1:02}"
        source = None if offline else get_background(search_terms[i], scene_dir)
        if source is None:
            source = procedural_background(scene_dir / "procedural.mp4", clip_len)
        paths.append(scene_dir / "cut.mp4")
        sources.append({"search": search_terms[i], "source": source.get("source"), "credit": source.get("credit")})
        # Long clips are trimmed, short clips loop. Every cut uses identical encoding.
        run([tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-stream_loop", "-1",
             "-i", str(Path(source["path"]).resolve()), "-t", f"{clip_len:.3f}", "-an",
             "-vf", "scale=540:960:force_original_aspect_ratio=increase,crop=540:960,fps=24,hue=s=0,eq=contrast=1.16",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "25",
             str(paths[-1].resolve())])
    listing = folder / "cuts.txt"
    listing.write_text("\n".join(f"file '{p.resolve()}'" for p in paths), encoding="utf-8")
    output = folder / "montage.mp4"
    run([tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
         "-i", str(listing), "-c", "copy", "-movflags", "+faststart", str(output)])
    return {"path": output, "source": "licensed stock video montage or original visuals",
            "credit": "; ".join(str(x["credit"]) for x in sources), "scenes": sources}

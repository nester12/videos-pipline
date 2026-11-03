"""Build dark cinematic short-form B-roll edits from licensed stock footage.

Never pretend a stock person is delivering the voice of an unrelated source.
On-camera speaking footage must come from the authentic speaker-video mode.
"""
from __future__ import annotations
import math
from pathlib import Path
from .backgrounds import get_background, procedural_background
from .common import PipelineError, run, tool

VISUAL_SEARCHES = (
    "lonely athlete running outdoors dawn",
    "man boxing punching bag dark gym",
    "athlete sprint training empty track",
    "silhouette running in rain",
    "person climbing mountain at sunrise",
    "athlete exhausted after workout",
    "runner jogging city night",
    "weight lifting training gym closeup",
    "man walking street rainy night",
)

def montage(visual_query: str, folder: Path, seconds: float, *, offline: bool = False,
            preview: bool = False) -> dict:
    """Render several distinct dark B-roll shots, timed to the real speech.

    Avoid procedural filler in real production. Without licensed footage, report a
    clear error instead of publishing unrelated or low-quality graphics.
    """
    folder.mkdir(parents=True, exist_ok=True)
    total=max(1.0, float(seconds))
    target_cut=4.0 if preview else 5.8
    n=min(len(VISUAL_SEARCHES), max(3, math.ceil(total / target_cut)))
    # The query is only useful when related to the chosen topic. Do not request
    # 'motivational speaker': that produced an unrelated person speaking.
    query=str(visual_query or "").lower()
    if any(k in query for k in ("runner", "athlete", "workout", "boxing", "gym", "mountain")) and not any(k in query for k in ("speech", "speaker", "conference", "presenter")):
        search_terms=(visual_query,) + tuple(x for x in VISUAL_SEARCHES if x!=visual_query)
    else:
        search_terms=VISUAL_SEARCHES
    paths, sources=[],[]
    for i in range(n):
        clip_len=total/n if i<n-1 else total-total/n*(n-1)
        folder_i=folder / f"scene_{i+1:02}"
        keyword=search_terms[i]
        source=None if offline else get_background(keyword, folder_i)
        if source is None:
            if not offline:
                raise PipelineError(f"No licensed cinematic footage found for '{keyword}'. "
                                    "Failing rather than creating a misleading speaker clip.")
            source=procedural_background(folder_i / "procedural.mp4", clip_len)
        target=folder_i / "cut.mp4"
        paths.append(target)
        sources.append({"query":keyword,"source":source.get("source"),"credit":source.get("credit")})
        run([tool("ffmpeg"),"-hide_banner","-loglevel","error","-y",
             "-stream_loop","-1","-i",str(Path(source["path"]).resolve()),
             "-t",f"{clip_len:.3f}","-an",
             "-vf","scale=540:960:force_original_aspect_ratio=increase,crop=540:960,"
                   "fps=24,hue=s=0.20,eq=contrast=1.18:brightness=-0.045",
             "-c:v","libx264","-pix_fmt","yuv420p","-preset","veryfast",
             "-crf","25",str(target.resolve())])
    listing=folder/"cuts.txt"
    listing.write_text("\n".join(f"file '{p.resolve()}'" for p in paths), encoding="utf-8")
    output=folder/"montage.mp4"
    run([tool("ffmpeg"),"-hide_banner","-loglevel","error","-y","-f","concat",
         "-safe","0","-i",str(listing),"-c","copy","-movflags","+faststart",str(output)])
    return {"path":output,"source":"licensed cinematic training montage",
            "credit":"; ".join(str(x["credit"]) for x in sources),
            "style":"dark, low-saturation, fast-cut emotional B-roll (not the original speaker)",
            "scenes":sources,"scene_count":len(sources)}

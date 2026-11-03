"""Produce vertical video, burn captions, and mix original instrumental with narration."""
from __future__ import annotations
import subprocess
from pathlib import Path
from .common import PipelineError, duration, run, stamp, tool


def write_srt(cues: list[dict], target: Path) -> Path:
    if not cues:
        raise PipelineError("Cannot render captions: speech transcript is empty")
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for n, cue in enumerate(cues, 1):
        start, end = float(cue["start"]), float(cue["end"])
        if end <= start:
            continue
        text = str(cue["text"]).strip().replace("\n", " ")
        if len(text) > 72:
            import textwrap
            text = "\n".join(textwrap.wrap(text, width=34))
        lines.append(f"{n}\n{stamp(start)} --> {stamp(end)}\n{text}\n")
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def render_video(speech: Path, backdrop: Path, srt: Path, music: Path,
                 destination: Path, *, preview=False) -> Path:
    """Loop supplied video to speech length; caption overlay; deterministic duration."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    length = duration(speech)
    if length < 2:
        raise PipelineError("Speech audio is too short")
    # Relative filename used inside -vf avoids Windows/Unix FFmpeg subtitles escaping bugs.
    # Render in SRT directory so subtitles=filename works.
    captions = srt.resolve()
    subtitle_arg = "subtitles=" + captions.name + ":force_style='FontName=DejaVu Sans,FontSize=11,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Alignment=2,MarginV=54,Bold=1'"
    filters = ("scale=540:960:force_original_aspect_ratio=increase,crop=540:960,"
               "fps=24,format=yuv420p,hue=s=0,eq=contrast=1.16:brightness=-0.035," + subtitle_arg)
    filter_graph = f"[0:v]{filters}[v];[1:a]aresample=44100,volume=1.35[voice];[2:a]aresample=44100,volume=0.35[bg];[voice][bg]amix=inputs=2:duration=first:dropout_transition=0,alimiter=limit=0.90[a]"
    command = [tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-stream_loop", "-1", "-i", str(backdrop.resolve()),
               "-i", str(speech.resolve()), "-i", str(music.resolve()), "-filter_complex", filter_graph,
               "-map", "[v]", "-map", "[a]", "-t", f"{length:.3f}", "-c:v", "libx264", "-preset", "veryfast",
               "-crf", "27" if preview else "23", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
               str(destination.resolve())]
    subprocess.run(command, cwd=captions.parent, check=True)
    return destination

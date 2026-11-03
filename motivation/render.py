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


def render_video(speech: Path, backdrop: Path, srt: Path, music: Path | None,
                 destination: Path, *, preview=False, speaker_start: float | None = None) -> Path:
    """Loop supplied video to speech length; caption overlay; deterministic duration."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    length = duration(speech)
    if length < 2:
        raise PipelineError("Speech audio is too short")
    # Relative filename used inside -vf avoids Windows/Unix FFmpeg subtitles escaping bugs.
    # Render in SRT directory so subtitles=filename works.
    captions = srt.resolve()
    subtitle_arg = "subtitles=" + captions.name + ":force_style='FontName=DejaVu Sans,FontSize=11,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Alignment=2,MarginV=54,Bold=1'"
    if speaker_start is not None:
        filters = ("scale=540:650:force_original_aspect_ratio=decrease,"
                   "pad=540:960:(ow-iw)/2:(oh-ih)/2:black,"
                   "fps=24,format=yuv420p,hue=s=0,eq=contrast=1.16:brightness=-0.035," + subtitle_arg)
    else:
        filters = ("scale=540:960:force_original_aspect_ratio=increase,crop=540:960,"
                   "fps=24,format=yuv420p,hue=s=0,eq=contrast=1.16:brightness=-0.035," + subtitle_arg)
    fade_out = max(0.0, length - 1.5)
    if music is None:
        # Preserve the source recording. Do not introduce another possibly-overlapping soundtrack.
        filter_graph = (f"[0:v]{filters}[v];"
                        f"[1:a]aresample=44100,highpass=f=90,"
                        f"loudnorm=I=-17:TP=-2:LRA=11,alimiter=limit=0.92[a]")
    else:
        filter_graph = (f"[0:v]{filters}[v];"
            f"[1:a]aresample=44100,highpass=f=90,loudnorm=I=-17:TP=-2:LRA=11,"
            f"asplit=2[voice_for_duck][voice_mix];"
            f"[2:a]aresample=44100,volume=0.40,afade=t=in:st=0:d=1.1,"
            f"afade=t=out:st={fade_out:.3f}:d=1.5[bed];"
            f"[bed][voice_for_duck]sidechaincompress=threshold=0.025:ratio=10:attack=25:release=450[ducked];"
            f"[voice_mix][ducked]amix=inputs=2:duration=first:normalize=0,"
            f"alimiter=limit=0.92[a]")
    visual_input = (["-stream_loop", "-1", "-i", str(backdrop.resolve())]
                    if speaker_start is None else ["-ss", f"{speaker_start:.3f}", "-i", str(backdrop.resolve())])
    soundtrack_input = (["-stream_loop", "-1", "-i", str(music.resolve())] if music else [])
    command = [tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", *visual_input,
               "-i", str(speech.resolve()), *soundtrack_input, "-filter_complex", filter_graph,
               "-map", "[v]", "-map", "[a]", "-t", f"{length:.3f}", "-c:v", "libx264", "-preset", "veryfast",
               "-crf", "27" if preview else "23", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
               str(destination.resolve())]
    subprocess.run(command, cwd=captions.parent, check=True)
    return destination

"""Extract the original human speech and preserve synchronized on-camera footage."""
from __future__ import annotations
import subprocess
from pathlib import Path
from urllib.parse import urlsplit
from .common import PipelineError, download, duration, tool

def licensed_video(url: str, directory: Path, *, rights_confirmed: bool) -> dict:
    if not rights_confirmed:
        raise PipelineError("Speaker-video permission not confirmed. In the GitHub Run workflow form tick rights_confirmed ONLY if you own or may reuse BOTH audio and footage; or select automatic licensed-speech search. CLI equivalent: --rights-confirmed")
    host=(urlsplit(url).hostname or "").lower()
    if host not in ("res.cloudinary.com","upload.wikimedia.org","archive.org"):
        raise PipelineError("Speaker video must be a public Cloudinary, Wikimedia or Archive URL")
    ext=Path(urlsplit(url).path).suffix.lower()
    if ext not in (".mp4",".mov",".m4v",".webm"):
        raise PipelineError("Speaker video must be MP4, MOV or WEBM")
    directory.mkdir(parents=True,exist_ok=True)
    path=download(url,directory/("speaker"+ext),max_mb=125)
    if duration(path)<8:
        raise PipelineError("Speaker video is too short")
    wav=directory/"speaker_audio.wav"
    subprocess.run([tool("ffmpeg"),"-hide_banner","-loglevel","error","-y",
                    "-i",str(path),"-vn","-ar","16000","-ac","1",str(wav)],check=True)
    return {"audio":wav,"video":path,
            "source":{"origin":url,"license":"rights confirmed by operator",
                      "reuse_requires_review":True,"voice":"real recorded human speech",
                      "type":"on-camera speaker"}}

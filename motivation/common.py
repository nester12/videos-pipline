from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import requests


class PipelineError(RuntimeError):
    pass


def tool(name: str) -> str:
    result = shutil.which(name)
    if not result:
        raise PipelineError(f"Missing executable: {name}. Install it before running.")
    return result


def run(args: list[str], **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def duration(path: Path) -> float:
    p = run([tool("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], capture_output=True, text=True)
    return float(p.stdout.strip())


def stamp(t: float) -> str:
    n = max(0, int(round(t * 1000)))
    h, n = divmod(n, 3600000)
    m, n = divmod(n, 60000)
    s, n = divmod(n, 1000)
    return f"{h:02}:{m:02}:{s:02},{n:03}"


def save_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def download(url: str, target: Path, max_mb=65) -> Path:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise PipelineError("Only HTTPS media links are accepted")
    target.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with requests.get(url, stream=True, timeout=(15, 70), allow_redirects=True) as response:
        response.raise_for_status()
        with target.open("wb") as f:
            for chunk in response.iter_content(1024 * 256):
                total += len(chunk)
                if total > max_mb * 1024 * 1024:
                    target.unlink(missing_ok=True)
                    raise PipelineError(f"Source larger than {max_mb} MB limit")
                f.write(chunk)
    if total < 1024:
        raise PipelineError("Downloaded media is suspiciously small")
    return target


def bool_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "yes", "true", "on")

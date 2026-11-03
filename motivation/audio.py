"""Recorded voice separation only: synthetic background music is disabled."""
from __future__ import annotations
import subprocess
from pathlib import Path
from .common import PipelineError
def demucs_vocals(path: Path, output: Path) -> Path:
    import importlib.util
    if importlib.util.find_spec("demucs") is None:
        raise PipelineError("Demucs is not installed. Enable separation in GitHub Actions.")
    subprocess.run(["python","-m","demucs","--two-stems=vocals","-o",str(output),str(path)],check=True)
    results=list(output.glob("**/vocals.wav"))
    if not results:
        raise PipelineError("Demucs did not produce a vocal stem")
    return results[0]

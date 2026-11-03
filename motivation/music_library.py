"""Curated, recorded CC0 cinematic music. No generated soundtrack."""
from __future__ import annotations
import hashlib
import html
from pathlib import Path
import requests
from .common import PipelineError, download, duration

API = "https://commons.wikimedia.org/w/api.php"
TRACKS = {
    "intense": "File:John Bartmann - dark-dyne-master.ogg",
    "determined": "File:John Bartmann - dark-dyne-master.ogg",
    "calm": "File:John Bartmann - bowed-voices-master.ogg",
    "hopeful": "File:John Bartmann - ethereal-moments-master.webm",
}
CC0_URL = "https://creativecommons.org/publicdomain/zero/1.0/"

def commons_track(mood: str, directory: Path, *, title: str | None = None) -> dict:
    title = title or TRACKS.get(mood, TRACKS["determined"])
    if title not in TRACKS.values():
        raise PipelineError("Soundtrack not in vetted CC0 catalogue")
    response = requests.get(API, params={
        "action":"query","format":"json","formatversion":"2","prop":"imageinfo",
        "iiprop":"url|extmetadata","titles":title,
    }, headers={"User-Agent":"MotivationVideoPipeline/3.0 (educational GitHub project)"}, timeout=35)
    response.raise_for_status()
    pages = response.json().get("query",{}).get("pages",[])
    if not pages or "imageinfo" not in pages[0]:
        raise PipelineError("Soundtrack unavailable on Wikimedia Commons")
    info = pages[0]["imageinfo"][0]
    ext = info.get("extmetadata", {})
    name = html.unescape(ext.get("LicenseShortName",{}).get("value","")).strip().lower()
    license_url = ext.get("LicenseUrl",{}).get("value","")
    if not (name in ("cc0","cc0 1.0") or "publicdomain/zero/1.0" in license_url.lower()):
        raise PipelineError("Soundtrack is not currently tagged CC0")
    url = info.get("url","")
    if not url.startswith("https://upload.wikimedia.org/"):
        raise PipelineError("Unexpected music download host")
    ext = Path(url.split("?")[0]).suffix.lower()
    if ext not in (".ogg",".oga",".webm",".opus"):
        raise PipelineError("Unsupported music file format")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ("music-" + hashlib.sha256(title.encode()).hexdigest()[:10] + ext)
    if not path.exists():
        download(url,path,max_mb=70)
    if duration(path) < 25:
        raise PipelineError("Soundtrack is too short")
    return {"path":path,"title":title.removeprefix("File:"),
            "artist":"John Bartmann","origin":"https://commons.wikimedia.org/wiki/"+title.replace(" ","_"),
            "license":CC0_URL,"type":"recorded instrumental","rights_review_required":False}

def select_music(directory: Path, *, mood="determined", music_path="", music_rights_confirmed=False) -> dict:
    if music_path:
        if not music_rights_confirmed:
            raise PipelineError("Custom soundtrack requires --music-rights-confirmed")
        path = Path(music_path).resolve()
        if not path.is_file() or duration(path) < 4:
            raise PipelineError("Custom soundtrack unavailable or too short")
        return {"path":path,"origin":"user provided licensed music","license":"operator-confirmed",
                "title":path.name,"type":"recorded instrumental","rights_review_required":True}
    return commons_track(mood,directory)

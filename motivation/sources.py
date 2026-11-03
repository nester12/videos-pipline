"""Licensing-first Internet Archive discovery. YouTube key is for discovery only."""
from __future__ import annotations
import re
from pathlib import Path
from urllib.parse import quote
import requests
from .common import PipelineError, download

ARCHIVE = "https://archive.org"
ALLOWED = (
    "creativecommons.org/publicdomain/zero/",
    "creativecommons.org/publicdomain/mark/",
    "creativecommons.org/licenses/by/",
)


def accepted_license(raw: str) -> bool:
    raw = (raw or "").lower().replace("https://", "").replace("http://", "")
    return any(x in raw for x in ALLOWED) and not any(x in raw for x in ("/by-nc", "/by-nd"))


def search_archive(query: str = "motivational speech", rows: int = 40):
    params = {"q": f'mediatype:audio AND ({query})', "fl[]": ["identifier", "title", "licenseurl"],
              "rows": rows, "output": "json", "sort[]": "downloads desc"}
    r = requests.get(ARCHIVE + "/advancedsearch.php", params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("response", {}).get("docs", [])


def discover_archive(query: str = "speech", max_candidates: int = 30):
    """Return candidate metadata; a matching license does NOT guarantee ownership."""
    hits = search_archive(query, max_candidates)
    for hit in hits:
        license_url = hit.get("licenseurl", "")
        if isinstance(license_url, list):
            license_url = license_url[0] if license_url else ""
        yield {"identifier": hit["identifier"], "title": hit.get("title", "Untitled"),
               "license": license_url, "eligible": accepted_license(license_url),
               "item_url": ARCHIVE + "/details/" + hit["identifier"]}


def licensed_audio(query: str, dest: Path, max_files: int = 20) -> dict:
    """Download explicitly CC0/PD/CC BY audio with track provenance and size bounds."""
    errors = []
    for hit in discover_archive(query, max_files):
        if not hit["eligible"]:
            continue
        try:
            r = requests.get(ARCHIVE + "/metadata/" + quote(hit["identifier"], safe=""), timeout=25)
            r.raise_for_status()
            details = r.json()
            actual_license = details.get("metadata", {}).get("licenseurl", "")
            if isinstance(actual_license, list):
                actual_license = actual_license[0] if actual_license else ""
            if not accepted_license(actual_license):
                continue
            tracks = [f for f in details.get("files", []) if
                      f.get("name", "").lower().endswith((".mp3", ".ogg", ".m4a", ".wav")) and
                      f.get("source", "") in ("original", "derivative")]
            tracks.sort(key=lambda f: (f.get("source") != "original", int(f.get("size", "0") or "0")))
            for track in tracks:
                size = int(track.get("size", "0") or "0")
                if size and not 1024 < size < 55 * 1024 * 1024:
                    continue
                name = track["name"]
                if "/" in name or ".." in name:
                    continue
                remote = ARCHIVE + "/download/" + quote(hit["identifier"], safe="") + "/" + quote(name)
                ext = Path(name).suffix.lower()
                download(remote, dest.with_suffix(ext), max_mb=55)
                return {"path": str(dest.with_suffix(ext)), "origin": hit["item_url"], "license": actual_license,
                        "title": hit["title"], "attribution": details.get("metadata", {}).get("creator", "unknown")}
        except (requests.RequestException, ValueError, PipelineError) as exc:
            errors.append(str(exc)[:180])
    raise PipelineError("No verifiably licensed downloadable Archive recording found. Supply your own licensed speech file. " + "; ".join(errors[:2]))


def youtube_suggestions(query: str, limit: int = 5):
    """Metadata search only; API does not permit downloading arbitrary YouTube media."""
    import os
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        return []
    r = requests.get("https://www.googleapis.com/youtube/v3/search", params={
        "part": "snippet", "q": query, "type": "video", "videoLicense": "creativeCommon", "maxResults": limit,
        "key": key}, timeout=25)
    r.raise_for_status()
    return [{"title": i["snippet"]["title"], "url": "https://youtube.com/watch?v=" + i["id"]["videoId"],
             "note": "Discovery only: obtain independent download and audio reuse permission"} for i in r.json().get("items", [])]

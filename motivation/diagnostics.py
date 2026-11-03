"""Safe read-only checks for configured APIs; never logs credentials or writes posts."""
from __future__ import annotations
import os
import requests


def service_health() -> dict:
    status = {}

    def test(name, keys, call):
        if not all(os.getenv(k) for k in keys):
            status[name] = {"status": "skipped", "reason": "not all credentials set"}
            return
        try:
            details = call()
            status[name] = {"status": "ok", "details": str(details)[:160]}
        except Exception as exc:
            # Avoid including token-bearing request URLs or exception text.
            status[name] = {"status": "failed", "type": type(exc).__name__}

    def buffer_probe():
        from .publish import buffer_channels
        return f"{len(buffer_channels())} channels discovered (details withheld from public CI logs)"

    def gemini_probe():
        key = os.environ['GEMINI_API_KEY']
        resp = requests.get('https://generativelanguage.googleapis.com/v1beta/models',
                            headers={'x-goog-api-key': key}, timeout=22)
        resp.raise_for_status()
        available = [m.get('name', '').split('/')[-1] for m in resp.json().get('models', [])
                     if 'generateContent' in m.get('supportedGenerationMethods', [])]
        return f"{len(available)} generation models available"

    def pexels_probe():
        resp = requests.get('https://api.pexels.com/v1/videos/search',
                            headers={'Authorization': os.environ['PEXELS_API_KEY']},
                            params={'query': 'running', 'per_page': 1}, timeout=22)
        resp.raise_for_status()
        return f"{len(resp.json().get('videos', []))} search results"

    def pixabay_probe():
        resp = requests.get('https://pixabay.com/api/videos/',
                            params={'key': os.environ['PIXABAY_API_KEY'], 'q': 'running', 'per_page': 3}, timeout=22)
        resp.raise_for_status()
        return f"{len(resp.json().get('hits', []))} search results"

    def cloudinary_probe():
        import cloudinary
        import cloudinary.api
        cloudinary.config(cloud_name=os.environ['CLOUDINARY_CLOUD_NAME'],
                          api_key=os.environ['CLOUDINARY_API_KEY'],
                          api_secret=os.environ['CLOUDINARY_API_SECRET'], secure=True)
        cloudinary.api.ping()
        return 'authenticated API ping succeeded'

    def youtube_probe():
        resp = requests.get('https://www.googleapis.com/youtube/v3/search', params={
            'part': 'snippet', 'q': 'motivational speech', 'maxResults': 1,
            'type': 'video', 'key': os.environ['YOUTUBE_API_KEY']}, timeout=22)
        resp.raise_for_status()
        return 'metadata search succeeded (not a download permission)'

    test('Buffer', ['BUFFER_API_KEY'], buffer_probe)
    test('Gemini', ['GEMINI_API_KEY'], gemini_probe)
    test('Pexels', ['PEXELS_API_KEY'], pexels_probe)
    test('Pixabay', ['PIXABAY_API_KEY'], pixabay_probe)
    test('Cloudinary', ['CLOUDINARY_CLOUD_NAME', 'CLOUDINARY_API_KEY', 'CLOUDINARY_API_SECRET'], cloudinary_probe)
    test('YouTube metadata', ['YOUTUBE_API_KEY'], youtube_probe)
    status['Freesound'] = {'status': 'unused', 'reason': 'automated downloads disabled until API commercial-use rights confirmed'}
    return status

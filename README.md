# Zero-Cost Short-Video Growth Pipeline

This repository builds 25-55 second vertical videos from live trend signals. It is designed to maximize controllable quality factors—topic freshness, hook strength, factuality, visual pacing, script density, and account-specific learning—without promising any fixed follower or view count.

## £0 rule

The project is intentionally restricted to free/local components. There is no paid fallback. Use a Google AI Studio project with billing disabled; if the free Gemini quota is unavailable, production must stop rather than charge. The repository is public so standard GitHub-hosted Actions runners are free. Pexels is used only through its free API.

## Pipeline

1. Google Trends RSS + optional YouTube Data API discover current topics in GB/US.
2. Safety filter removes unsuitable topics.
3. Deterministic ranking weighs freshness, velocity, category fit, account learning, and repetition.
4. Gemini creates a grounded fact pack using Google Search, then runs a 6-hook tournament and 3-script tournament.
5. Only a script above the configured quality floor is allowed to continue.
6. The script becomes 7-9 scene beats; Pexels supplies fresh portrait footage.
7. Kokoro generates narration locally.
8. FFmpeg creates a 1080x1920 multi-scene edit with grouped captions.
9. QA checks duration, 9:16 video, audio, and decodability.
10. The workflow exports `final.mp4`, `caption.txt`, and `metadata.json`.
11. TikTok direct posting stays disabled until official OAuth/scopes/audit requirements are satisfied.

## Required free credentials

Create credentials only from the official providers:

- Gemini API key: https://aistudio.google.com/apikey
- Pexels API key: https://www.pexels.com/api/key/
- YouTube Data API key (optional but recommended): https://console.cloud.google.com/apis/credentials
- TikTok developer app later: https://developers.tiktok.com/

Add GitHub repository secrets named `GEMINI_API_KEY`, `PEXELS_API_KEY`, and optionally `YOUTUBE_API_KEY`. Never commit secrets.

## Important Gemini safeguard

Create/use a Google project with billing disabled. The code uses only explicitly allow-listed models that currently expose a free tier and has no paid provider fallback.

## Current publishing mode

V1 uses `export_only`: GitHub Actions creates the final publish package as a short-lived artifact. TikTok integration code only constructs official API payloads. Do not send or store a TikTok password.

## Local tests

```bash
pip install -r requirements.txt
PYTHONPATH=src pytest -q
python -m compileall -q src
```

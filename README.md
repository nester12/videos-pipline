# Real Human-Voice Motivational Video Pipeline

This pipeline is built for dark, cinematic motivational edits featuring the **original recorded voices of real people**. The production paths contain **no text-to-speech** and do not generate synthetic instrumental music. The TikTok example videos are styling references, not a licence to copy their music, speeches, or footage.

## How it works
1. Obtain a licensed recording of someone speaking (search Internet Archive for CC0/public-domain/CC BY audio with publisher assertions, or provide an authorised original speaker MP4 from Cloudinary).
2. Check for existing music. If needed, run optional Demucs to separate the human voice. No additional soundtrack is layered on uncertain/unreviewed audio.
3. Transcribe with faster-whisper and select a coherent passage, optionally using Gemini for **editing decisions only**, not for any voice generation.
4. If an actual speaker MP4 is provided, show the original speaker on-camera with dark grading and black letterbox framing. For licensed audio-only speeches, assemble a grayscale Pexels/Pixabay montage.
5. Download recorded cinematic instrumentals from the curated **Wikimedia Commons CC0** catalogue. Current picks by John Bartmann include dark-dyne, bowed-voices and ethereal-moments. Metadata is checked at runtime, with provenance saved to result.json.
6. Normalize the human voice, automatically duck the music under speech, fade music in/out and burn synchronized captions.
7. Save final.mp4 and captions as GitHub Actions artifacts. Cloudinary upload and Buffer draft/queue require permission confirmation. No automatic public publishing.

## GitHub Actions
- **1 — Test Video**: find licensed human speech with Archive, or use a direct Cloudinary MP4 recording of an authorized speaker. Cloudinary upload is off by default.
- **2 — Test Posting**: check Buffer channel IDs without posting, or explicitly create a draft or queued post from a reviewed Cloudinary video URL.
- **3 — Real speaker video and optional Buffer posting**: use Archive or an approved speaker MP4; output artifacts even when social posting is off.
- **0 — Validate**: automatic tests and read-only service health checks on push.

## Local examples
Requires Python 3.11+, FFmpeg/ffprobe (built with libass), and dependencies from requirements.txt.

```bash
python -m pip install -r requirements.txt
python -m motivation doctor
python -m motivation discover --query "motivational speech"
python -m motivation test-video --source archive --query "motivational speech"
python -m motivation full-video --source archive --query "motivational speech" --separate-music
python -m motivation full-video --source clip --speaker-video-url 'https://res.cloudinary.com/your-cloud/video/upload/approved.mp4' --rights-confirmed --clean-confirmed
python -m pytest -q
```

For a locally licensed speech-only recording:
```bash
python -m motivation full-video --source audio --speech-path approved.wav --rights-confirmed --clean-confirmed
```

Use a separately licensed recording as soundtrack with `--music-path music.mp3 --music-rights-confirmed`.

## Rights and limitations
A Creative Commons label on an Internet Archive item is **not verified ownership**; a human must review source rights before uploading or posting. Other audio in the speech, images of individuals, film/music rights and platform licensing can still matter. If no suitable human speech recording is found, the pipeline **fails rather than changing to an AI narrator**. Auto discovery cannot guarantee a specific celebrity or motivational quote. Music files are from Wikimedia Commons, with claimed CC0 status checked at runtime; recordings still merit review. Freesound API downloads are intentionally unused due to free-API commercial terms.

## Costs and secrets
No paid TTS or music-generation API is used. GitHub Actions, Cloudinary, speech-analysis CPU, stock-video and Buffer quotas may apply. Secrets are set in GitHub Actions Settings; no credentials are committed. Known optional secrets are `GEMINI_API_KEY`, `PEXELS_API_KEY`, `PIXABAY_API_KEY`, `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`, `BUFFER_API_KEY`.

## Files
`motivation/cli.py` orchestrates; `speaker.py` handles licensed on-camera videos; `music_library.py` selects verified-licence recordings; `discovery.py` searches speech; `analysis.py` transcribes and selects; `render.py` makes the final mix and subtitles.

The preceding v2 prototype used Piper neural voices and synthesized music. Those production paths have been replaced; any leftover v2 helper code is deprecated and not invoked by these three workflows.

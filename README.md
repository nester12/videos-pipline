# Motivational Video Pipeline — Version 2

Three independent, manually triggered GitHub Actions pipelines built for free-tier operation. Previous version preserved at `backup-2026-11-03` branch. **No recurring automated publishing, paid voice services or paid music APIs.** A full production run uploads an MP4 to Cloudinary and only creates Buffer posts when `draft` or `queue` is deliberately selected.

## Workflows

| Workflow | Purpose | Default consequence |
| --- | --- | --- |
| **1 - Test Video** (`01-test-video.yml`) | Offline male neural voice, cinematic original soundtrack, one stock clip where available, high-contrast black-and-white captions, optional Cloudinary upload | Creates downloadable artifact; does NOT publish |
| **2 - Test Posting** (`02-test-posting.yml`) | Read Buffer channels; optionally create one explicitly requested video draft/queue post. Creates a test video and Cloudinary upload when URL left empty | `check` only; no post |
| **3 - Full Video and Posting** (`03-full-video.yml`) | Source speech or generate original script; extract/score speech; assemble 2–5 distinct Pexels/Pixabay clips or original fallback; original cinematic music; timed subtitles; render/upload to Cloudinary; optional Buffer submission | Video upload; posting off |
| **0 - Validation** (`00-validation.yml`) | On code changes: unit tests and real offline render; a second job tries neural TTS and *read-only* service probes | No public posts or social draft mutations |

## Voice and media

- **Offline, male neural TTS**: Piper `en_US-john-medium` (rhasspy/Piper; model card documents public-domain LibriVox training data). Model ~64 MB downloaded to GitHub Actions cache, never committed.
- **Original words**: optional Gemini script generator; fails back to a predefined original script and logs its origin. If a free API key is missing/blocked, the pipeline stays runnable, but output quality may drop.
- **Licensed-source discovery**: Internet Archive with explicit CC0/public-domain or CC BY metadata, then speech/music inspection, transcription with faster-whisper and passage ranking. Archive items are uploader-asserted licensing, **not independently cleared rights**; a human review is required before publishing an Archive recording. YouTube is discovery-only, never auto-downloaded.
- **Music detection**: optional inaSpeechSegmenter, or manual approval for user-owned clean audio. Speech-over-music classification is uncertain; overlap can go undetected. Optional Demucs performs vocal isolation, but **cannot guarantee perfect source separation**. If no trustworthy clean speech is found, `auto` records its fallback to original speech; strict `archive` fails instead.
- **Stock footage**: Pexels with Pixabay fallback, up to five individual clips with matching searches, resized and rendered into a vertical 540 × 960 montage. If stock API credentials/footage are unavailable, original abstract visuals are generated (the workflow remains operational but video quality is lower).
- **Music**: new original synthetic cinematic chord progression with low pulse/percussion, matched to mood; not a third-party copyright claim. Quality remains different from professionally recorded licensed tracks.
- **Burned captions**: timestamps from Whisper words or known original TTS sentence durations.

## GitHub Secrets

```text
GEMINI_API_KEY
YOUTUBE_API_KEY
PEXELS_API_KEY
PIXABAY_API_KEY
CLOUDINARY_CLOUD_NAME
CLOUDINARY_API_KEY
CLOUDINARY_API_SECRET
BUFFER_API_KEY
FREESOUND_API_KEY
```

Freesound is intentionally not used in this release: its API and individual asset commercial-use permissions must be confirmed first. No invented or extra secrets are needed. Optional environment `GEMINI_MODEL` can select a model available to your key (default `gemini-2.5-flash`).

## First-use validation

1. Go to **Actions → 0 - Validate pipeline and connected APIs** after the code update. Read both job statuses and download the preview artifact. The second job must successfully download and synthesize with Piper; this is tested on GitHub, not locally.
2. Go to **Actions → 1 - Test Video**, leave Cloudinary upload off. Review `motivational-test-preview` artifact. Switch upload on only after this succeeds.
3. Go to **Actions → 2 - Test Posting**, select `check`. Inspect the Buffer channel IDs in the workflow output (your repo is public, so don't post sensitive info). Next, choose `draft`, give the connected channel ID, and leave `video_url` empty if you want a newly generated Cloudinary test video. Review draft in Buffer. **Never select `queue` for a harmless test.**
4. Go to **Actions → 3 - Full Video and Posting**, use `audio_source=original`, `posting_mode=off` first. This creates a full video, uploads to Cloudinary, and saves a GitHub artifact. For reusing internet speech, select `archive` or `auto` and read the output's origin/licensing report.
5. Choose `draft` for a real publication candidate only after reviewing its audio, wording and footage. `queue` schedules a real social post and requires explicit selection and valid channel ID.

## Locally

Requires Python 3.11+, FFmpeg with libass, and 

```sh
pip install -r requirements.txt piper-tts
python -m motivation doctor
python -m motivation doctor --live # read-only API checks
python -m motivation test-video --offline
python -m motivation full-video --source original --offline
pytest -q
```

On Windows, install FFmpeg separately. `MOTIVATION_VOICE=espeak` plus installed eSpeak is a **diagnostic-only** fallback that sounds robotic; it is used for fast offline CI to avoid downloading the neural voice model. Full workflows use Piper without silent fallback.

## Limits and safety

- Commercial reuse rights of uploaded or discovered recordings must be evaluated. A Creative Commons tag on YouTube is **not** permission to download arbitrary audio or use its music.
- Full-run quality depends on footage availability, speech quality, API quotas, and local CPU. Do not treat a successful software test as proof that every chosen speech is suitable for publication.
- Live Buffer and Cloudinary behaviour requires credentials and connected channels; local unit tests use mocks. The validation workflow uses safe read-only checks; only a separately requested `draft`/`queue` run can test Buffer post creation.
- GitHub Actions free minutes, Cloudinary storage/bandwidth, Gemini and stock-video API quotas vary. This project does not deliberately enable billing or auto-charge, but external service accounts must stay on no-cost plans.
- Keep your repo public if relying on GitHub Actions public-repository quotas; never commit tokens or private files.

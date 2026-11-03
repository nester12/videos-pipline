# Motivational Video Pipeline — New £0 Prototype

A new product intended to **replace** the contents of `nester12/videos-pipline`. Its three GitHub Actions workflows are independent and manually triggered to avoid automatic usage charges. The previous repository's history should be preserved with a backup branch before replacement.

## Three GitHub Actions workflows

| Workflow | Purpose | Does it publish? |
| --- | --- | --- |
| **1 — Test Video (safe preview)** | Creates a short original-narration black-and-white MP4 with timed captions and self-generated music. Optional Cloudinary upload. | **Never** |
| **2 — Test Posting (Buffer)** | Checks Buffer account and lists channels; optionally creates a **draft** using a provided public Cloudinary video URL, or generates and uploads a test video automatically. | Default **check only**; can explicitly select `draft` or `queue` |
| **3 — Full Video and Posting** | Generates a speech, transcribes or uses known narration timing, Gemini scores/selects a section, obtains background footage, renders captions + music, uploads Cloudinary, and optionally submits to Buffer. | Default **off**; can explicitly select `draft` or `queue` |

**IMPORTANT:** "queue" is not a harmless test. It schedules a real social post via Buffer and only runs when a human explicitly selects it and supplies a channel ID. A Buffer channel must already be connected to a supported social network.

## Quick start on GitHub

1. Back up your old `main` branch before replacement, then upload this ZIP's **contents** to the root of `videos-pipline` (see replacement instructions below). Never upload secrets or `.env`.
2. Open **Actions → 1 - Test Video (safe preview) → Run workflow**, leaving Cloudinary upload unchecked. Download `motivational-test-preview` from the run artifacts.
3. Open **Actions → 2 - Test Posting (Buffer) → Run workflow**, choose `check`. Read the **Verify API** step to list your connected Buffer channels and their IDs.
4. Run **2 - Test Posting** again: select `draft`, enter the correct channel ID, leave video URL empty to generate a test video and upload it to Cloudinary. Review the created post in Buffer. It will **not** be queued.
5. Run **3 - Full Video and Posting** with `audio_source=original` and `posting_mode=off` for the most reliable first production test. The MP4 is uploaded to Cloudinary and saved as a downloadable Actions artifact.
6. After reviewing output, run `posting_mode=draft` with the correct channel ID, and only then consider `queue` if you explicitly want it scheduled.

**Secrets already expected** (`Settings → Secrets and variables → Actions`):

- `GEMINI_API_KEY` (optional; original script generation and excerpt selection, local fallback if unavailable)
- `PEXELS_API_KEY` (optional; free footage, falls back to Pixabay or locally generated background)
- `PIXABAY_API_KEY` (optional; alternative free footage)
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` (required for uploads)
- `BUFFER_API_KEY` (required for Buffer tests or scheduling)
- `YOUTUBE_API_KEY` (optional discovery *only*; YouTube data APIs do not grant download/reuse rights)
- `FREESOUND_API_KEY` (reserved for a future license-checked music importer; not required by this version)

The system uses original, locally synthesized background music. Freesound is deliberately *not* used automatically because of licensing and API non-commercial restrictions. No paid TTS or music service is needed. Narration uses free **eSpeak**, which works but sounds robotic; production-quality voice will need a properly licensed audio source or later voice upgrade.

## Rights and audio safety

The pipeline never assumes a TikTok or YouTube speech is licensed just because it can be played. YouTube results are metadata leads only. Internet Archive search checks for explicit CC0/public-domain or CC BY licenses and additionally checks item metadata, but these claims still deserve human review. Imported audio must have reuse rights confirmed.

**Music detection:** Optional `inaSpeechSegmenter` can label obvious music; without it, music is **unknown**, not "clean". When source is `auto`, the pipeline rejects unverified Archive speech and uses original, dry narration instead. You can optionally install Demucs locally for vocal separation, but separated output must be reviewed. Don't bypass `--clean-confirmed` without listening. To respect the preference for speech-only voiceovers, only confirmed dry narration is used by default.

## Free-tier budget

- No recurring schedules, no paid workers, no automatic API upgrades.
- GitHub public-repository standard Actions minutes, Buffer free-tier API, Gemini free-tier access and media host quotas may have restrictions. **Zero cost does not guarantee unlimited runs.**
- Do not attach a billed Google Cloud account or enable pay-as-you-go quotas if you want strict £0 operation.
- Full video length is selected from message coherence and emotional payoff. It is not forced to exceed 80 seconds. Test video is intentionally about 16 seconds.

## Local development

Prerequisites: Python 3.11+, FFmpeg + ffprobe with libass/subtitles, eSpeak / eSpeak NG.

```bash
python -m pip install -r requirements.txt
python -m motivation doctor
python -m motivation test-video --offline
python -m motivation full-video --source original --offline
python -m motivation discover --query speech
pytest -q
```

To use a speech file you own or have permission to reuse:

```bash
python -m motivation full-video --speech-path ./licensed-speech.mp3 --rights-confirmed --clean-confirmed
```

To attempt a public-domain speech from Internet Archive, install `inaSpeechSegmenter` (optional heavyweight classifier) and run:

```bash
python -m motivation full-video --source archive --query 'inspirational speech'
```

If its music status cannot be verified, the tool **stops**, instead of incorrectly adding music over existing copyrighted music. Manual overrides exist for material you have already reviewed.

To upload the full result:

```bash
python -m motivation full-video --source original --upload
```

To test Buffer safely:

```bash
python -m motivation test-posting --mode check
python -m motivation test-posting --mode draft --channel-id YOUR_CHANNEL_ID --video-url https://res.cloudinary.com/YOUR_CLOUD/video/upload/yourvideo.mp4
```

Only `--mode queue` schedules a post. You must opt into it deliberately.

## Replace the existing GitHub repository (Windows PowerShell)

The connected GitHub write operation was blocked in this session. The ZIP is ready to install manually. These commands preserve the old code in a backup branch **before** replacing tracked files:

```powershell
git clone https://github.com/nester12/videos-pipline.git
cd videos-pipline
git branch backup-before-motivation-prototype
git push origin backup-before-motivation-prototype
# Remove the old tracked project files from main:
git rm -r -- .
# Extract the ZIP to a temporary location, e.g. C:\Temp\motivation-new
# Copy all extracted CONTENTS (including .github and .gitignore) here:
Get-ChildItem -Force 'C:\Temp\motivation-new' | Copy-Item -Destination . -Recurse -Force
git add -A
git commit -m "Replace old video pipeline with motivational prototype"
git push origin main
```

If the extracted ZIP contains a top-level folder, copy **that folder's contents**, not the folder itself. Keep the `.git` folder in the cloned repository untouched. Git history and the backup branch allow recovery. GitHub repository **secrets survive** code replacement.

## Current prototype limits

- External API credentials were not available in this local test environment, so **Cloudinary/Buffer/Gemini/stock-video endpoints have not been tested live**.
- Offline preview and offline full-video rendering have been run locally; unit tests pass.
- Original voice is a prototype TTS, not professional-sounding narration.
- This is a functioning integration prototype, **not** a promise of virality, fully automatic third-party speech clearance, or unlimited free video production.
- Background uses a simple original monochrome abstract fallback when stock APIs return no results. Pexels/Pixabay footage is preferred when accessible.

## API documentation

- [Buffer authentication](https://developers.buffer.com/guides/authentication)
- [Buffer video post](https://developers.buffer.com/examples/create-video-post.html)
- [Pexels API](https://www.pexels.com/api/documentation/)
- [Internet Archive APIs](https://archive.org/developers/)

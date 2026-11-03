# Real Human-Voice Motivational Video Pipeline

This pipeline is built for dark, cinematic motivational edits featuring the **original recorded voices of real people**. The production paths contain **no text-to-speech** and do not generate synthetic instrumental music. The TikTok example videos are styling references, not a licence to copy their music, speeches, or footage.

## Why the initial Cloudinary test looked wrong

The first live test used narration from a LibriVox audiobook with **unrelated conference footage**, a single continuous scene, no verified replacement soundtrack, and subtitles at the bottom. That was not representative of your reference examples.

**The automatic mode now creates a short-cut, low-saturation athlete/training montage and rejects known audiobooks**. It will not show unrelated speaker stock video that appears to mouth another person's audio. Speaker-on-camera mode uses the actual permitted source video so audio and mouth movements remain connected. The caption alignment has been adjusted toward the reference's centred minimalist format.

The cinematic montage is still an approximation, not a guarantee of the emotional voice, copyrighted film/anime footage, or exact music from your references. Unverified musical backgrounds are not layered. Public output requires source rights review.

## Start here: clearly named GitHub Actions

- **0 - CHECK SYSTEM:** runs tests and checks connected services; no video or post.
- **1 - CREATE SAMPLE VIDEO:** automatically uploads private MP4s to **Cloudinary Media Library > motivation-test-previews**. Choose **Cinematic montage (licensed speech audio)** or **Actual speaker on camera (my licensed video)**. The latter needs a direct MP4 URL and **rights_confirmed** only if you have permission.
- **2 - CHECK BUFFER / MAKE DRAFT:** check accounts, create a nonpublic draft, or explicitly queue a post. Default is a harmless check.
- **3 - CREATE FULL VIDEO:** same two real-voice source options, plus a clear choice between making an MP4 only, saving a Buffer draft, or queueing a real post. Default: video only.

### If GitHub says "Importing a real speaker video requires --rights-confirmed"

That message means you selected a speaker video but did not confirm rights to reuse its audio AND footage. For your own or otherwise authorized video, tick **rights_confirmed** in the Run workflow form. Otherwise use **Find licensed human speech automatically** and leave the URL empty. A TikTok page link is not a supported direct video URL and does not itself give reuse rights.

A speaker-video URL will now be **ignored if automatic search is selected**; it no longer silently triggers imported-video mode.

## Important: GitHub runner disk-space fix

The previous sample failed before rendering because **inaSpeechSegmenter installed TensorFlow plus massive CUDA/GPU packages**, exhausting GitHub Actions disk space. Sample and full-video workflows now install only normal Python video dependencies. CPU-only voice separation is off by default and experimental.

When the recording contains music or its music status is unknown, the pipeline preserves **the real person's original recorded audio**, and intentionally does not add a second cinematic soundtrack. This avoids accidental music overlap. To layer the new CC0 cinematic soundtrack on a supplied clip, select **clean_confirmed** only after listening to it and verifying that the source speech has no music.

An Archive item licence is only a claim; review the source and audio rights before uploading or publishing it. There are **no AI-generated narrators**.

## How it works
1. Obtain a licensed recording of someone speaking (search Internet Archive for CC0/public-domain/CC BY audio with publisher assertions, or provide an authorised original speaker MP4 from Cloudinary).
2. Check for existing music. If needed, run optional Demucs to separate the human voice. No additional soundtrack is layered on uncertain/unreviewed audio.
3. Transcribe with faster-whisper and select a coherent passage, optionally using Gemini for **editing decisions only**, not for any voice generation.
4. If an actual speaker MP4 is provided, show the original speaker on-camera with dark grading and black letterbox framing. For licensed audio-only speeches, assemble a grayscale Pexels/Pixabay montage.
5. Download recorded cinematic instrumentals from the curated **Wikimedia Commons CC0** catalogue. Current picks by John Bartmann include dark-dyne, bowed-voices and ethereal-moments. Metadata is checked at runtime, with provenance saved to result.json.
6. Normalize the human voice, automatically duck the music under speech, fade music in/out and burn synchronized captions.
7. Save final.mp4 and captions as GitHub Actions artifacts. Every test-video upload is automatically saved as an **authenticated** Cloudinary asset under `motivation-test-previews`, even for automatically found Archive speech. This is a private review copy; it cannot be publicly viewed through the unsigned Cloudinary URL. Public full-video uploads and Buffer drafts/queue still require rights review. No automatic public publishing.

## GitHub Actions
- **1 — Test Video**: find licensed human speech with Archive, or use a direct Cloudinary MP4 recording of an authorized speaker. Cloudinary upload is **automatic and private** on every successful test. Look in **Cloudinary Media Library → motivation-test-previews**. You can also download the MP4 from the GitHub Actions artifact.
- **2 — Test Posting**: check Buffer channel IDs without posting, or explicitly create a draft or queued post from a reviewed Cloudinary video URL.
- **3 — Real speaker video and optional Buffer posting**: use Archive or an approved speaker MP4; output artifacts even when social posting is off.
- **0 — Validate**: automatic tests and read-only service health checks on push.

## Local examples
Requires Python 3.11+, FFmpeg/ffprobe (built with libass), and dependencies from requirements.txt.

```bash
python -m pip install -r requirements.txt
python -m motivation doctor
python -m motivation discover --query "motivational speech"
python -m motivation test-video --source archive --query "motivational speech" --upload
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

**Preview validation:** On-camera mode and cinematic B-roll mode should be reviewed separately for visual/audio quality; technical upload success is not equivalent to matching the references.

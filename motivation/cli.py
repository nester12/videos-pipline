"""Three runnable pipelines: test-video, test-posting, and full-video."""
from __future__ import annotations
import argparse
import json
import os
import subprocess
from pathlib import Path
from .analysis import gemini_original_script, gemini_selection, gemini_model, music_check, original_narration, shift_cues, slice_audio, transcribe
from .audio import demucs_vocals, make_music
from .scenes import montage
from .common import PipelineError, duration, save_json, tool
from .publish import buffer_channels, buffer_post, upload_cloudinary
from .render import render_video, write_srt
from .sources import discover_archive, youtube_suggestions
from .discovery import select_archive_recording


def produce(folder: Path, *, preview=False, source="auto", speech_path="", rights_confirmed=False,
            clean_confirmed=False, query="speech", upload=False, post="off", channel_id="",
            separate_music=False, allow_unknown_music=False, offline=False, archive_reviewed=False) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    archive_failure = None
    source_info = None
    selected = None
    check = None
    cues = []
    if speech_path:
        if not rights_confirmed:
            raise PipelineError("You must confirm reuse rights with --rights-confirmed for imported speech")
        if not clean_confirmed and not separate_music and not allow_unknown_music:
            raise PipelineError("External audio requires music review; use --clean-confirmed, --separate-music or --allow-unknown-music")
        audio = Path(speech_path).resolve()
        if not audio.is_file():
            raise PipelineError(f"Speech audio does not exist: {audio}")
        source_info = {"origin": "user-provided licensed speech", "license": "rights confirmed by operator"}
    elif preview or source == "original":
        generated_script = None if preview else gemini_original_script(query)
        made = original_narration(folder / "tts", generated_script)
        audio, cues = made["path"], made["cues"]
        source_info = {"origin": made["origin"], "license": "original", "voice": made.get("voice", ""), "script_source": "Gemini" if generated_script else "built-in original script"}
    else:
        try:
            chosen = select_archive_recording(query, folder / "archive_speech", separate_music=separate_music,
                                               clean_confirmed=clean_confirmed,
                                               allow_unknown_music=allow_unknown_music)
            audio = Path(chosen["path"])
            cues = chosen["cues"]
            selected = chosen["selection"]
            check = chosen["music_check"]
            source_info = {k: v for k, v in chosen["source"].items() if k != "path"}
        except Exception as exc:
            if source == "archive":
                raise
            archive_failure = str(exc)[:300]
            generated_script = gemini_original_script(query)
            made = original_narration(folder / "tts", generated_script)
            audio, cues = made["path"], made["cues"]
            source_info = {"origin": made["origin"], "license": "original", "voice": made.get("voice", ""), "script_source": "Gemini" if generated_script else "built-in original script"}

    if not cues:
        check = music_check(audio)
        if separate_music and check["status"] != "likely_clean":
            audio = demucs_vocals(audio, folder / "separation")
            check = music_check(audio)
            check["warning"] = "Demucs attempted vocal separation; manual review still recommended"
        if check["status"] != "likely_clean" and not (clean_confirmed or allow_unknown_music):
            if source == "auto" and not speech_path:
                # Fail closed on unverified music, but generate an original demo so the workflow remains operational.
                archive_failure = "Archive speech music status unverified; generated original narration instead"
                generated_script = gemini_original_script(query)
                made = original_narration(folder / "tts", generated_script)
                audio, cues = made["path"], made["cues"]
                source_info = {"origin": made["origin"], "license": "original", "voice": made.get("voice", ""), "script_source": "Gemini" if generated_script else "built-in original script"}
            else:
                raise PipelineError("Music detection uncertain or music present; need clean audio confirmation or reviewed separation")
        if not cues:
            cues = transcribe(audio)
            if not cues:
                raise PipelineError("No intelligible speech found")
    elif check is None:
        check = {"status": "no_external_music", "reason": "Generated from original dry narration"}

    # Preview uses a concise excerpt; full length is chosen by Gemini, with no fixed output duration.
    if preview:
        selection = {"start": 0.0, "end": min((next((c["end"] for c in cues if c["end"] >= 15), cues[-1]["end"])), duration(audio)),
                     "mood": "determined", "visual_query": "runner training outdoors",
                     "score": 7, "reason": "short preview of original speech"}
    else:
        selection = selected or gemini_selection(cues)
    cut_start = max(0.0, float(selection["start"]))
    cut_end = min(duration(audio), float(selection["end"]))
    if cut_end - cut_start < 2:
        raise PipelineError("Selected speech clip too short")
    speech = folder / "speech_selected.wav"
    slice_audio(audio, speech, cut_start, cut_end)
    captions = write_srt(shift_cues(cues, cut_start, cut_end), folder / "captions.srt")
    music = make_music(folder / "original_music.wav", duration(speech), selection["mood"])
    background = montage(selection["visual_query"], folder / "scenes", duration(speech), offline=offline, preview=preview)
    video = render_video(speech, Path(background["path"]), captions, music, folder / "final.mp4", preview=preview)
    result = {"video": str(video), "seconds": round(duration(video), 2), "selection": selection,
              "source": source_info, "background": {k: v for k, v in background.items() if k != "path"},
              "music_check": check, "archive_fallback_reason": archive_failure,
              "music": "original locally synthesized cinematic instrumental",
              "voice": source_info.get("voice", "licensed recording"),
              "rights_review_required": bool(speech_path or source_info.get("reuse_requires_review") or
                                              source_info.get("license", "").startswith("http")),
              "model": gemini_model()}
    if post != "off" and source_info.get("reuse_requires_review") and not archive_reviewed:
        raise PipelineError("Archive recordings require a human rights review before creating any Buffer post. Use --archive-reviewed after checking the actual recording and license")
    if upload or post != "off":
        result["cloudinary_url"] = upload_cloudinary(video)
    if post != "off":
        words = " ".join(c["text"] for c in cues if c["end"] >= cut_start and c["start"] <= cut_end)
        description = (words[:220].rsplit(" ", 1)[0] if len(words) > 220 else words) + "\n#motivation #discipline"
        if source_info.get("license", "").startswith(("http://creativecommons.org/licenses/by/", "https://creativecommons.org/licenses/by/")):
            description += ("\nSpeech attribution: " + str(source_info.get("title", "Speech")) +
                            " by " + str(source_info.get("attribution", "Unknown creator")) + 
                            " — " + str(source_info["license"]) + " — " + str(source_info.get("origin", "")))
        result["buffer_post"] = buffer_post(result["cloudinary_url"], channel_id, description, post)
    save_json(folder / "result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description="Free-tier motivational video prototype")
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("test-video", "full-video"):
        p = subs.add_parser(name)
        p.add_argument("--output", default=f"output/{name}")
        p.add_argument("--upload", action="store_true")
        p.add_argument("--offline", action="store_true")
        p.add_argument("--channel-id", default="")
        p.add_argument("--post", choices=["off", "draft", "queue"], default="off")
        p.add_argument("--source", choices=["auto", "original", "archive"], default="auto")
        p.add_argument("--query", default="speech")
        p.add_argument("--speech-path", default="")
        p.add_argument("--rights-confirmed", action="store_true")
        p.add_argument("--clean-confirmed", action="store_true")
        p.add_argument("--separate-music", action="store_true")
        p.add_argument("--allow-unknown-music", action="store_true")
        p.add_argument("--archive-reviewed", action="store_true", help="I have reviewed Archive source and rights before posting")
    p = subs.add_parser("test-posting")
    p.add_argument("--video-url", default="")
    p.add_argument("--channel-id", default="")
    p.add_argument("--mode", choices=["check", "draft", "queue"], default="check")
    p = subs.add_parser("discover")
    p.add_argument("--query", default="speech")
    p.add_argument("--youtube", action="store_true")
    p = subs.add_parser("doctor")
    p.add_argument("--live", action="store_true", help="Read-only API connectivity tests")
    args = parser.parse_args()
    try:
        if args.command in ("test-video", "full-video"):
            result = produce(Path(args.output), preview=args.command == "test-video", source=args.source,
                   speech_path=args.speech_path, rights_confirmed=args.rights_confirmed,
                   clean_confirmed=args.clean_confirmed, query=args.query, upload=args.upload,
                   post=args.post, channel_id=args.channel_id, separate_music=args.separate_music,
                   allow_unknown_music=args.allow_unknown_music, offline=args.offline,
                   archive_reviewed=args.archive_reviewed)
        elif args.command == "test-posting":
            channels = buffer_channels()
            result = {"channels": channels, "mode": args.mode}
            if args.mode != "check":
                if not args.channel_id:
                    raise PipelineError("Provide --channel-id. Discover channels with --mode check first")
                if not args.video_url:
                    raise PipelineError("Provide a public Cloudinary direct video URL")
                result["post"] = buffer_post(args.video_url, args.channel_id,
                           "Motivational video pipeline test. #motivation", args.mode)
        elif args.command == "discover":
            result = {"archive": list(discover_archive(args.query))}
            if args.youtube:
                result["youtube_suggestions"] = youtube_suggestions(args.query)
        else:
            import shutil
            result = {"ffmpeg": bool(shutil.which("ffmpeg")), "ffprobe": bool(shutil.which("ffprobe")),
                      "espeak": bool(shutil.which("espeak-ng") or shutil.which("espeak")),
                      "keys_present": {n: bool(os.getenv(n)) for n in ["YOUTUBE_API_KEY", "GEMINI_API_KEY", "PEXELS_API_KEY",
                      "PIXABAY_API_KEY", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET", "CLOUDINARY_CLOUD_NAME", "BUFFER_API_KEY"]}}
            if args.live:
                from .diagnostics import service_health
                result["integrations"] = service_health()
                if any(x.get("status") == "failed" for x in result["integrations"].values()):
                    save_json(Path("output/diagnostics.json"), result)
                    print(json.dumps(result, indent=2))
                    parser.exit(2, "One or more configured integrations failed; see output/diagnostics.json\n")
        print(json.dumps(result, indent=2, default=str))
    except (PipelineError, ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Pipeline error: {exc}\n")


if __name__ == "__main__":
    main()

"""Three runnable pipelines: test-video, test-posting, and full-video."""
from __future__ import annotations
import argparse
import json
import os
import subprocess
from pathlib import Path
from .analysis import gemini_selection, music_check, shift_cues, slice_audio, transcribe
from .audio import demucs_vocals
from .scenes import montage
from .common import PipelineError, duration, save_json, tool
from .publish import buffer_channels, buffer_post, upload_cloudinary
from .render import render_video, write_srt
from .sources import discover_archive, youtube_suggestions
from .discovery import select_archive_recording
from .music_library import select_music
from .speaker import licensed_video


def produce(folder: Path, *, preview=False, source="auto", speech_path="",
            speaker_video_url="", rights_confirmed=False, clean_confirmed=False,
            query="motivational speech", upload=False, post="off", channel_id="",
            separate_music=False, allow_unknown_music=False, offline=False,
            archive_reviewed=False, music_path="", music_rights_confirmed=False) -> dict:
    """Fail closed: never synthesize voices or soundtracks."""
    folder.mkdir(parents=True,exist_ok=True)
    if preview and post!="off":
        raise PipelineError("Test videos are private Cloudinary previews, not social posts. Use the full-video workflow for drafts/queue.")
    source_info, selected, check, cues, speaker_visual = None,None,None,[],None
    if source=="original":
        raise PipelineError("AI generated voices are disabled. Select auto, archive, clip or audio.")
    if source=="clip":
        if not speaker_video_url:
            raise PipelineError("Clip source needs --speaker-video-url")
        record=licensed_video(speaker_video_url,folder/"original_speaker",rights_confirmed=rights_confirmed)
        audio=record["audio"]
        speaker_visual=record["video"]
        source_info=record["source"]
    elif source=="audio":
        if not speech_path:
            raise PipelineError("Audio source requires --speech-path")
        if not rights_confirmed:
            raise PipelineError("Imported real human speech requires --rights-confirmed")
        audio=Path(speech_path).resolve()
        if not audio.is_file():
            raise PipelineError("Speech audio file not found")
        source_info={"origin":"user-provided speech recording","license":"operator-confirmed",
                     "voice":"real recorded human speech","reuse_requires_review":True}
    elif source in ("auto","archive"):
        if offline:
            raise PipelineError("Automatic licensed speech discovery needs internet; use a local audio recording")
        try:
            chosen=select_archive_recording(query,folder/"archive_speech",
                      separate_music=separate_music,clean_confirmed=False,allow_unknown_music=True)
        except Exception as exc:
            raise PipelineError("No suitable licensed real-person speech found; no AI substitute will be generated. "+str(exc)[:400]) from exc
        audio=Path(chosen["path"])
        cues=chosen["cues"]
        selected=chosen["selection"]
        check=chosen["music_check"]
        source_info={k:v for k,v in chosen["source"].items() if k!="path"}
        source_info["voice"]="real recorded human speech"
    else:
        raise PipelineError("Invalid speech source")
    if not cues:
        check=music_check(audio)
        if check["status"]!="likely_clean" and separate_music:
            audio=demucs_vocals(audio,folder/"isolated_voice")
            check=music_check(audio)
            check["manual_review"]="Separated recording requires human listening review"
        if check["status"]!="likely_clean" and not clean_confirmed:
            check["soundtrack_policy"]="Keep original audio; no added music until source is reviewed"
        cues=transcribe(audio)
        if not cues:
            raise PipelineError("No intelligible real human speech detected")
    if preview:
        cut_end=next((c["end"] for c in cues if c["end"]-cues[0]["start"]>=18),cues[-1]["end"])
        selection={"start":float(cues[0]["start"]),"end":min(float(cut_end),duration(audio)),
                   "mood":"determined","visual_query":"dramatic motivational speaker",
                   "score":6,"reason":"Short human speech preview"}
    else:
        selection=selected or gemini_selection(cues)
    cut_start=max(0.,float(selection["start"]))
    cut_end=min(duration(audio),float(selection["end"]))
    if cut_end-cut_start<3:
        raise PipelineError("Chosen recording passage is too short")
    speech=folder/"human_speech.wav"
    slice_audio(audio,speech,cut_start,cut_end)
    captions=write_srt(shift_cues(cues,cut_start,cut_end),folder/"captions.srt")
    # Never layer a second soundtrack over music that may already be present.
    # Without the huge classifier we cannot honestly claim source audio is clean.
    verified_clean=(check.get("status")=="likely_clean" or clean_confirmed)
    if check.get("status")=="music_detected":
        verified_clean=False
    if verified_clean:
        music=select_music(folder/"soundtracks",mood=selection.get("mood","determined"),
                           music_path=music_path,music_rights_confirmed=music_rights_confirmed)
    else:
        music={"path":None,"title":"Original recording only","type":"original audio preserved",
               "warning":"Existing background music has not been verified; no new music added"}
    if speaker_visual:
        background={"path":speaker_visual,"source":source_info["origin"],
                    "style":"speaker on camera, black letterbox framing"}
    else:
        background=montage(selection.get("visual_query","cinematic runner training"),
                           folder/"scenes",duration(speech),offline=offline,preview=preview)
    video=render_video(speech,Path(background["path"]),captions,
                       Path(music["path"]) if music["path"] else None,
                       folder/"final.mp4",preview=preview,
                       speaker_start=cut_start if speaker_visual else None)
    result={"video":str(video),"seconds":round(duration(video),2),
            "selection":selection,"source":source_info,
            "voice":"original recorded human voice (no TTS)",
            "music":{k:str(v) for k,v in music.items() if k!="path"},
            "background":{k:v for k,v in background.items() if k!="path"},
            "music_check":check,
            "rights_review_required":bool(source_info.get("reuse_requires_review") or music.get("rights_review_required")),
            "posting_mode":post,
            "soundtrack_added":bool(music["path"]),
            "music_classification":check.get("status")}
    save_json(folder/"result.json",result)
    private_preview=bool(preview and post=="off")
    if (upload or post!="off") and source_info.get("reuse_requires_review") and not (archive_reviewed or rights_confirmed or private_preview):
        raise PipelineError("Review actual Archive recording rights before publicly uploading or publishing")
    if upload or post!="off":
        result["cloudinary_url"]=upload_cloudinary(video, authenticated_preview=private_preview)
        result["cloudinary_delivery"]="authenticated" if private_preview else "public"
        result["cloudinary_folder"]="motivation-test-previews" if private_preview else "motivation-prototype"
        if private_preview:
            result["cloudinary_note"]="Preview is saved in Cloudinary Media Library under motivation-test-previews. The unsigned URL is access-controlled and cannot be used for Buffer posting."
        print("Cloudinary upload confirmed:", result["cloudinary_folder"], "-", result["cloudinary_delivery"])
    if post!="off":
        words=" ".join(c["text"] for c in cues if c["end"]>=cut_start and c["start"]<=cut_end)
        description=(words[:220].rsplit(" ",1)[0] if len(words)>220 else words)+"\n#motivation #discipline"
        if source_info.get("title"):
            description+=f'\nSpeech: {source_info["title"]} by {source_info.get("attribution","Unknown")} — {source_info.get("origin","")} — {source_info.get("license","")}'
        description+=f'\nMusic: {music.get("title","")} by {music.get("artist","")} ({music.get("license","")})'
        result["buffer_post"]=buffer_post(result["cloudinary_url"],channel_id,description,post)
    save_json(folder/"result.json",result)
    return result


def main():
    parser = argparse.ArgumentParser(description="Real-person speech video pipeline with recorded music and no AI voice")
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("test-video", "full-video"):
        p = subs.add_parser(name)
        p.add_argument("--output", default=f"output/{name}")
        p.add_argument("--upload", action="store_true")
        p.add_argument("--offline", action="store_true")
        p.add_argument("--channel-id", default="")
        p.add_argument("--post", choices=["off", "draft", "queue"], default="off")
        p.add_argument("--source", choices=["auto", "archive", "clip", "audio"], default="auto")
        p.add_argument("--query", default="motivational speech")
        p.add_argument("--speech-path", default="")
        p.add_argument("--speaker-video-url", default="")
        p.add_argument("--music-path", default="")
        p.add_argument("--music-rights-confirmed", action="store_true")
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
                   speech_path=args.speech_path, speaker_video_url=args.speaker_video_url,
                   music_path=args.music_path, music_rights_confirmed=args.music_rights_confirmed,
                   rights_confirmed=args.rights_confirmed,
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

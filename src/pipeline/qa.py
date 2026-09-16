import json, subprocess


def validate_probe(probe: dict, expected_min_s: float, expected_max_s: float) -> list[str]:
    errors=[]
    try: duration=float((probe.get('format') or {}).get('duration') or 0)
    except Exception: duration=0
    if duration < expected_min_s or duration > expected_max_s:
        errors.append(f'duration {duration:.1f}s outside {expected_min_s}-{expected_max_s}s')
    streams=probe.get('streams') or []
    videos=[s for s in streams if s.get('codec_type')=='video']
    audios=[s for s in streams if s.get('codec_type')=='audio']
    if not videos:
        errors.append('missing video stream')
    else:
        w=int(videos[0].get('width') or 0); h=int(videos[0].get('height') or 0)
        if not w or not h or abs((w/h)-(9/16)) > 0.03:
            errors.append(f'video is not 9:16 ({w}x{h})')
    if not audios:
        errors.append('missing audio stream')
    return errors


def validate_video(path: str, expected_min_s: float, expected_max_s: float) -> list[str]:
    p=subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',path], capture_output=True, text=True)
    if p.returncode != 0:
        return ['ffprobe could not decode output video']
    return validate_probe(json.loads(p.stdout), expected_min_s, expected_max_s)

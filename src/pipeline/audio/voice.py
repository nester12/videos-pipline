import os
import shutil
import subprocess
import numpy as np
import soundfile as sf

SAMPLE_RATE=24000


def get_duration(path: str) -> float:
    p=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',path],capture_output=True,text=True,check=True)
    return float(p.stdout.strip())


def synthesize_kokoro(text: str, output_path: str, voice: str = 'am_michael', speed: float = 1.0) -> str:
    if not shutil.which('ffmpeg'):
        raise RuntimeError('ffmpeg is required')
    try:
        from kokoro import KPipeline
    except ImportError as exc:
        raise RuntimeError('Kokoro is not installed') from exc
    pipeline=KPipeline(lang_code='a')
    parts=[]
    pause=np.zeros(int(SAMPLE_RATE*0.035),dtype=np.float32)
    for result in pipeline(' '.join(text.split()), voice=voice, speed=speed):
        audio=getattr(result,'audio',None)
        if audio is None:
            try: audio=result[2]
            except Exception: audio=None
        if audio is None: continue
        if hasattr(audio,'detach'): audio=audio.detach().cpu().numpy()
        audio=np.asarray(audio,dtype=np.float32).squeeze()
        if audio.size:
            if parts: parts.append(pause)
            parts.append(audio)
    if not parts:
        raise RuntimeError('Kokoro produced no audio')
    raw=output_path+'.raw.wav'
    sf.write(raw,np.concatenate(parts),SAMPLE_RATE)
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i',raw,'-af','loudnorm=I=-16:TP=-1.5:LRA=11',output_path],check=True)
    os.remove(raw)
    return output_path

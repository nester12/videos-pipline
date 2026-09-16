import subprocess


def _escape_sub_path(path: str) -> str:
    return path.replace('\\','/').replace(':','\\:').replace("'","\\'")


def build_render_command(scene_files: list[str], narration_path: str, output_path: str, duration: float, subtitle_path: str | None = None) -> list[str]:
    if not scene_files:
        raise ValueError('At least one scene file is required')
    cmd=['ffmpeg','-y']
    for path in scene_files:
        cmd += ['-stream_loop','-1','-i',path]
    cmd += ['-i',narration_path]
    n=len(scene_files); seg=max(duration/n,0.5)
    filters=[]; labels=[]
    for i in range(n):
        label=f'v{i}'
        filters.append(f'[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,trim=duration={seg:.3f},setpts=PTS-STARTPTS,eq=contrast=1.03:saturation=1.05[{label}]')
        labels.append(f'[{label}]')
    filters.append(''.join(labels)+f'concat=n={n}:v=1:a=0[vbase]')
    out_label='vbase'
    if subtitle_path:
        filters.append(f"[vbase]subtitles='{_escape_sub_path(subtitle_path)}'[vout]")
        out_label='vout'
    cmd += ['-filter_complex',';'.join(filters),'-map',f'[{out_label}]','-map',f'{n}:a','-t',str(duration),'-r','30','-c:v','libx264','-preset','fast','-crf','24','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart',output_path]
    return cmd


def render_short(scene_files: list[str], narration_path: str, output_path: str, duration: float, subtitle_path: str | None = None) -> str:
    subprocess.run(build_render_command(scene_files,narration_path,output_path,duration,subtitle_path),check=True)
    return output_path

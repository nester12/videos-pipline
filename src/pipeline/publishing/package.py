from pathlib import Path
import json, shutil


def build_caption(hook: str, hashtags: list[str]) -> str:
    clean=[]
    for tag in hashtags:
        tag=''.join(ch for ch in str(tag).lower() if ch.isalnum() or ch=='_')
        if tag and tag not in clean:
            clean.append(tag)
    tags=' '.join('#'+t for t in clean[:5])
    return (hook.strip() + ('\n\n'+tags if tags else '')).strip()


def write_publish_package(video_path: str, caption: str, metadata: dict, out_dir: str) -> str:
    out=Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    target=out/'final.mp4'
    if Path(video_path).resolve() != target.resolve():
        shutil.copyfile(video_path, target)
    (out/'caption.txt').write_text(caption, encoding='utf-8')
    (out/'metadata.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')
    return str(out)

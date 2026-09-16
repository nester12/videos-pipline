import requests

SEARCH_URL='https://api.pexels.com/videos/search'


def search_pexels_videos(query: str, api_key: str, per_page: int = 8, timeout: int = 20) -> list[dict]:
    r=requests.get(SEARCH_URL, params={'query':query,'per_page':per_page,'orientation':'portrait'}, headers={'Authorization':api_key}, timeout=timeout)
    r.raise_for_status()
    out=[]
    for video in r.json().get('videos',[]):
        width=int(video.get('width') or 0); height=int(video.get('height') or 0)
        files=video.get('video_files') or []
        if not files: continue
        best=max(files, key=lambda f:(int(f.get('height') or 0)*int(f.get('width') or 0)))
        out.append({'url':best.get('link'),'width':width,'height':height,'quality':best.get('quality',''),'pexels_url':video.get('url',''),'creator':(video.get('user') or {}).get('name','')})
    return out


def choose_best_video(videos: list[dict], recent_urls: set[str]) -> dict:
    candidates=[v for v in videos if v.get('url') and v.get('url') not in recent_urls]
    if not candidates: raise RuntimeError('No fresh Pexels video available')
    def score(v):
        portrait=1 if int(v.get('height',0)) > int(v.get('width',0)) else 0
        pixels=int(v.get('height',0))*int(v.get('width',0))
        return (portrait, pixels)
    return max(candidates,key=score)


def download_video(url: str, output_path: str, timeout: int = 60) -> str:
    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk: f.write(chunk)
    return output_path

from datetime import datetime, timezone
import requests
from .models import TrendCandidate

URL = 'https://www.googleapis.com/youtube/v3/videos'


def _category(category_id: str, title: str) -> str:
    if category_id == '20': return 'gaming'
    if category_id == '28': return 'technology'
    t = title.lower()
    return 'technology' if 'ai' in t or 'tech' in t else 'internet'


def parse_youtube_response(data: dict, region: str, now_iso: str | None = None) -> list[TrendCandidate]:
    now = datetime.fromisoformat(now_iso.replace('Z','+00:00')) if now_iso else datetime.now(timezone.utc)
    out = []
    for item in data.get('items', []):
        snippet = item.get('snippet', {})
        stats = item.get('statistics', {})
        title = str(snippet.get('title') or '').strip()
        if not title: continue
        published = str(snippet.get('publishedAt') or '')
        try:
            dt = datetime.fromisoformat(published.replace('Z','+00:00'))
            hours = max((now - dt).total_seconds()/3600.0, 1.0)
        except Exception:
            hours = 24.0
        views = float(stats.get('viewCount') or 0)
        velocity = views / hours
        freshness = max(0.05, min(1.0, 1.0 - min(hours, 168.0)/168.0))
        vid = str(item.get('id') or '')
        out.append(TrendCandidate(title, 'youtube', freshness, velocity, _category(str(snippet.get('categoryId') or ''), title), f'https://www.youtube.com/watch?v={vid}' if vid else '', region))
    return out


def fetch_youtube_trends(api_key: str, region: str, timeout: int = 20) -> list[TrendCandidate]:
    response = requests.get(URL, params={'part':'snippet,statistics','chart':'mostPopular','regionCode':region,'maxResults':25,'key':api_key}, timeout=timeout)
    response.raise_for_status()
    return parse_youtube_response(response.json(), region)

from datetime import datetime, timezone
import re
import requests
from .models import TrendCandidate

URL = 'https://www.googleapis.com/youtube/v3/videos'

TECH_TERMS = re.compile(r'\b(ai|artificial intelligence|openai|chatgpt|gemini|tech|technology|iphone|android|computer|robot|software|cyber|cybersecurity|app|browser)\b', re.I)
GAMING_TERMS = re.compile(r'\b(game|gaming|xbox|playstation|nintendo|steam|fortnite|minecraft|roblox)\b', re.I)
INTERNET_TERMS = re.compile(r'\b(internet|online|viral|reddit|tiktok|youtube|discord|streamer|meme|creator|social media)\b', re.I)
ENTERTAINMENT_CATEGORIES = {'1', '10', '17', '23', '24'}


def _category(category_id: str, title: str) -> str:
    if category_id == '20' or GAMING_TERMS.search(title):
        return 'gaming'
    if category_id == '28' or TECH_TERMS.search(title):
        return 'technology'
    if INTERNET_TERMS.search(title):
        return 'internet'
    if category_id in ENTERTAINMENT_CATEGORIES:
        return 'entertainment'
    return 'internet'


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

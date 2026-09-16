import re
from urllib.parse import urlparse

import requests

from pipeline.trends.models import TrendCandidate

GDELT_DOC_URL = 'https://api.gdeltproject.org/api/v2/doc/doc'


def _query_terms(value: str) -> str:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'_-]*", value or '')
    useful = [w for w in words if len(w) > 1][:8]
    if not useful:
        raise ValueError('Topic cannot be converted into a GDELT query')
    return ' '.join(useful)


def normalize_articles(payload: dict, limit: int = 8) -> list[dict]:
    out = []
    seen = set()
    for item in payload.get('articles', []) if isinstance(payload, dict) else []:
        if not isinstance(item, dict):
            continue
        title = str(item.get('title') or '').strip()
        url = str(item.get('url') or '').strip()
        if not title or not url or url in seen:
            continue
        parsed = urlparse(url)
        if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
            continue
        domain = str(item.get('domain') or parsed.netloc).strip().lower()
        out.append({
            'title': title[:300],
            'url': url,
            'domain': domain[:200],
            'seen_date': str(item.get('seendate') or '').strip()[:40],
        })
        seen.add(url)
        if len(out) >= limit:
            break
    return out


def fetch_articles(topic: str, *, timeout: int = 25, max_records: int = 12) -> list[dict]:
    params = {
        'query': _query_terms(topic),
        'mode': 'artlist',
        'maxrecords': max(1, min(int(max_records), 25)),
        'timespan': '1week',
        'sort': 'hybridrel',
        'format': 'json',
    }
    try:
        response = requests.get(
            GDELT_DOC_URL,
            params=params,
            timeout=timeout,
            headers={'User-Agent': 'zero-cost-video-pipeline/1.1'},
        )
        response.raise_for_status()
        return normalize_articles(response.json())
    except (requests.RequestException, ValueError):
        # GDELT is a best-effort free evidence source. A rate limit or outage
        # must never push the pipeline toward a paid fallback or crash CI.
        return []


def build_evidence_pack(topic: TrendCandidate, articles: list[dict]) -> dict:
    return {
        'topic': topic.title,
        'trend_source': topic.source,
        'trend_source_url': topic.source_url,
        'region': topic.region,
        'articles': list(articles)[:8],
        'evidence_status': 'current_articles_available' if articles else 'thin_evidence',
        'evidence_rule': (
            'Headlines and source links are current discovery evidence only. '
            'Do not infer details that are not supported by this evidence.'
        ),
    }

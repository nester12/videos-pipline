import json, os, re
from pathlib import Path
from .google_trends import fetch_google_trends
from .youtube import fetch_youtube_trends


def _key(title: str) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', title.lower()).strip()


def dedupe_trends(items):
    best = {}
    for item in items:
        k = _key(item.title)
        signal = item.velocity * (0.5 + item.freshness)
        old = best.get(k)
        if old is None or signal > old[0]:
            best[k] = (signal, item)
    return [x[1] for x in best.values()]


def collect_trends(config: dict):
    items = []
    for region in config.get('regions', ['GB']):
        try: items.extend(fetch_google_trends(region))
        except Exception as exc: print(f'Google Trends skipped: {exc}')
        key = os.getenv('YOUTUBE_API_KEY','').strip()
        if key:
            try: items.extend(fetch_youtube_trends(key, region))
            except Exception as exc: print(f'YouTube skipped: {exc}')
    return dedupe_trends(items)


def main():
    from pipeline.config import load_config
    items = collect_trends(load_config())
    Path('data').mkdir(exist_ok=True)
    payload=[x.__dict__ for x in items]
    Path('data/trends.json').write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Saved {len(payload)} trend candidates')

if __name__ == '__main__': main()

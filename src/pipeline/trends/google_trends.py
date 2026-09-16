import re
import xml.etree.ElementTree as ET
import requests
from .models import TrendCandidate

RSS_URL = 'https://trends.google.com/trending/rss?geo={region}'


def _traffic_to_number(text: str) -> float:
    cleaned = (text or '').upper().replace(',', '').replace('+', '').strip()
    m = re.match(r'([0-9.]+)([KMB]?)', cleaned)
    if not m:
        return 0.0
    value = float(m.group(1))
    return value * {'':1, 'K':1_000, 'M':1_000_000, 'B':1_000_000_000}[m.group(2)]


def _category(title: str) -> str:
    t = title.lower()
    if any(x in t for x in ('ai', 'iphone', 'android', 'computer', 'robot', 'tech')):
        return 'technology'
    if any(x in t for x in ('game', 'gaming', 'xbox', 'playstation', 'nintendo')):
        return 'gaming'
    return 'internet'


def parse_google_rss(xml_text: str, region: str) -> list[TrendCandidate]:
    root = ET.fromstring(xml_text)
    out = []
    ns = {'ht': 'https://trends.google.com/trending/rss'}
    for item in root.findall('.//item'):
        title = (item.findtext('title') or '').strip()
        if not title:
            continue
        traffic = item.findtext('ht:approx_traffic', default='', namespaces=ns)
        link = (item.findtext('link') or '').strip()
        velocity = _traffic_to_number(traffic)
        freshness = min(1.0, 0.55 + (velocity / 100_000.0)) if velocity else 0.55
        out.append(TrendCandidate(title, 'google_trends', min(freshness, 1.0), velocity, _category(title), link, region))
    return out


def fetch_google_trends(region: str, timeout: int = 20) -> list[TrendCandidate]:
    response = requests.get(RSS_URL.format(region=region), timeout=timeout, headers={'User-Agent':'zero-cost-video-pipeline/1.0'})
    response.raise_for_status()
    return parse_google_rss(response.text, region)

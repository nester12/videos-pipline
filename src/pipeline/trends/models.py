from dataclasses import dataclass


@dataclass(frozen=True)
class TrendCandidate:
    title: str
    source: str
    freshness: float
    velocity: float
    category: str
    source_url: str = ''
    region: str = 'GB'

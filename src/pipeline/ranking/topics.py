import math, re
from pipeline.safety.filter import is_safe_topic


def _norm(s: str) -> str:
    return re.sub(r'[^a-z0-9]+',' ',s.lower()).strip()


def score_topic(candidate, recent_topics: list[str], category_weights: dict[str,float]) -> float:
    category_weight = float(category_weights.get(candidate.category, 1.0))
    velocity_component = min(math.log10(max(candidate.velocity,0)+1)/6.0, 1.0)
    score = 100 * (0.45*candidate.freshness + 0.35*velocity_component + 0.20*min(category_weight/1.5, 1.0))
    if _norm(candidate.title) in {_norm(x) for x in recent_topics}:
        score *= 0.2
    return round(score, 3)


def rank_topics(candidates, recent_topics: list[str], category_weights: dict[str,float]):
    safe=[]
    for c in candidates:
        if c.category not in category_weights:
            continue
        ok,_=is_safe_topic(c.title)
        if ok: safe.append((score_topic(c,recent_topics,category_weights),c))
    safe.sort(key=lambda x:x[0], reverse=True)
    return [c for _,c in safe]

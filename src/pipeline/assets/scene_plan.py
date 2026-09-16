from dataclasses import dataclass
import re
from pipeline.writing.models import ScriptCandidate

@dataclass(frozen=True)
class SceneBeat:
    narration: str
    search_query: str
    emphasis: str = ''

STOP={'this','that','with','from','then','when','what','they','there','have','your','about','into','just','almost','finally','something','becomes'}


def _keywords(text: str) -> str:
    words=[w.lower() for w in re.findall(r"[A-Za-z0-9']+", text) if len(w)>3]
    picked=[]
    for w in words:
        if w not in STOP and w not in picked:
            picked.append(w)
    return ' '.join(picked[:4]) or 'technology internet'


def build_scene_plan(script: ScriptCandidate, target_beats: int = 8) -> list[SceneBeat]:
    sentences=[s.strip() for s in re.split(r'(?<=[.!?])\s+', script.text.strip()) if s.strip()]
    if not sentences:
        return []
    if len(sentences) < target_beats:
        chunks=[]
        for s in sentences:
            words=s.split()
            if len(words)>12:
                mid=len(words)//2
                chunks += [' '.join(words[:mid]), ' '.join(words[mid:])]
            else:
                chunks.append(s)
        sentences=chunks
    return [SceneBeat(s, _keywords(s), _keywords(s).split()[0].upper()) for s in sentences]

from .models import HookCandidate, ScriptCandidate


def normalize_hooks(payload: dict) -> list[HookCandidate]:
    out=[]
    for item in payload.get('hooks',[]):
        text=str(item.get('text') or '').strip()
        if text:
            out.append(HookCandidate(text, float(item.get('score') or 0)))
    return sorted(out, key=lambda x:x.score, reverse=True)


def choose_best_script(scripts: list[ScriptCandidate], minimum_score: float = 80) -> ScriptCandidate:
    eligible=[s for s in scripts if s.score >= minimum_score]
    if not eligible: raise RuntimeError('No script cleared the quality floor')
    return max(eligible, key=lambda s:s.score)

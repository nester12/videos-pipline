import json
from pipeline.trends.models import TrendCandidate
from pipeline.research.gdelt import build_evidence_pack, fetch_articles
from .models import HookCandidate, ScriptCandidate
from .tournament import normalize_hooks, choose_best_script


def build_research_prompt(topic: TrendCandidate, evidence: dict | None = None) -> str:
    evidence = evidence or build_evidence_pack(topic, [])
    return f'''FACT PACK\nCreate a concise current fact pack for the trending topic below. Return JSON only.\n\nTopic: {topic.title}\nTrend source: {topic.source}\nCurrent evidence: {json.dumps(evidence, ensure_ascii=False)}\n\nRules:\n- Use only the supplied evidence.\n- Do not invent facts, quotes, dates, numbers, motives, reactions, or source details.\n- Treat article headlines as discovery evidence, not proof of details that are not stated.\n- If evidence is thin or conflicting, explicitly say so in the summary and facts.\n- Keep only information useful for a 25-50 second short video.\n- Preserve the supplied source URLs in the sources list.\n\nReturn exactly: {{"summary":"...","facts":["..."],"search_terms":["..."],"sources":[{{"title":"...","url":"..."}}]}}'''


def _hook_prompt(topic: TrendCandidate, research: dict) -> str:
    return f'''HOOK TOURNAMENT\nCreate 6 original opening hooks for a short vertical video about: {topic.title}\nVerified research: {json.dumps(research, ensure_ascii=False)}\n\nEach hook must be understandable immediately, specific, truthful, and create curiosity without making a promise the video cannot satisfy. Avoid generic phrases such as "you won't believe". Score each 0-100 for stop-scroll strength, clarity, specificity, and payoff honesty. Return JSON: {{"hooks":[{{"text":"...","score":0}}]}}.'''


def _script_prompt(topic: TrendCandidate, research: dict, hooks: list[HookCandidate]) -> str:
    hook_text=[h.text for h in hooks[:3]]
    return f'''SCRIPT TOURNAMENT\nWrite 3 original short-form narration scripts about {topic.title}.\nVerified fact pack: {json.dumps(research, ensure_ascii=False)}\nUse one of these hooks: {json.dumps(hook_text, ensure_ascii=False)}\n\nTarget 80-130 words, usually 25-50 seconds. Start immediately with the hook. Add a meaningful new detail every few seconds. Use conversational spoken English, short sentences, and a clear payoff. Do not copy wording from sources. Do not invent facts. End cleanly without begging for follows or likes.\n\nScore each 0-100 for first-two-seconds strength, density, clarity, payoff, factual fidelity, and visual potential. Return JSON: {{"scripts":[{{"text":"...","hook":"...","score":0}}]}}.'''


def _normalize_scripts(payload: dict) -> list[ScriptCandidate]:
    out=[]
    for item in payload.get('scripts', []):
        text=str(item.get('text') or '').strip()
        hook=str(item.get('hook') or '').strip()
        if text and hook:
            out.append(ScriptCandidate(text, float(item.get('score') or 0), hook))
    return sorted(out, key=lambda x:x.score, reverse=True)


def generate_winning_script(topic: TrendCandidate, client, minimum_score: float = 82):
    articles = fetch_articles(topic.title)
    evidence = build_evidence_pack(topic, articles)
    research=client.generate_json(build_research_prompt(topic, evidence))
    hooks=normalize_hooks(client.generate_json(_hook_prompt(topic,research)))
    if len(hooks) < 2:
        raise RuntimeError('Hook tournament returned too few valid candidates')
    scripts=_normalize_scripts(client.generate_json(_script_prompt(topic,research,hooks)))
    winner=choose_best_script(scripts, minimum_score)
    return winner, research, hooks

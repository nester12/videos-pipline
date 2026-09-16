from pipeline.writing.production import build_research_prompt, generate_winning_script
from pipeline.trends.models import TrendCandidate
from pipeline.render.captions import build_ass_subtitles


class FakeClient:
    def __init__(self): self.calls=[]
    def generate_json(self, prompt, **kwargs):
        self.calls.append((prompt,kwargs))
        if 'FACT PACK' in prompt:
            return {'summary':'A verified update','facts':['fact one','fact two'],'search_terms':['AI update'],'sources':[{'title':'Source','url':'https://example.com'}]}
        if 'HOOK TOURNAMENT' in prompt:
            return {'hooks':[{'text':'Hook A','score':82},{'text':'Hook B','score':94}]}
        if 'SCRIPT TOURNAMENT' in prompt:
            return {'scripts':[{'text':'Hook B. Here is what changed and why it matters right now. The payoff is clear.', 'hook':'Hook B','score':91},{'text':'Other script','hook':'Hook A','score':75}]}
        raise AssertionError(prompt)


def test_research_prompt_requests_verifiable_fact_pack():
    topic=TrendCandidate('AI browser update','youtube',1,100,'technology','https://example.com')
    prompt=build_research_prompt(topic)
    assert 'AI browser update' in prompt
    assert 'sources' in prompt.lower()
    assert 'do not invent' in prompt.lower()


def test_generate_winning_script_runs_three_stage_tournament(monkeypatch):
    topic=TrendCandidate('AI browser update','youtube',1,100,'technology','https://example.com')
    monkeypatch.setattr('pipeline.writing.production.fetch_articles', lambda _: [
        {'title':'AI browser update','url':'https://example.com/story','domain':'example.com','seen_date':'20260916T120000Z'}
    ])
    client=FakeClient()
    result, research, hooks=generate_winning_script(topic, client, minimum_score=80)
    assert result.score==91
    assert hooks[0].text=='Hook B'
    assert research['summary']=='A verified update'
    assert len(client.calls)==3
    assert client.calls[0][1].get('use_google_search', False) is False


def test_ass_subtitles_generate_timed_grouped_dialogue():
    ass=build_ass_subtitles('one two three four five six seven eight', duration=8, max_words=4)
    assert '[Events]' in ass
    assert ass.count('Dialogue:')==2
    assert 'ONE TWO THREE FOUR' in ass


def test_audio_module_does_not_load_production_packages_at_import_time():
    import pipeline.audio.voice as voice
    assert 'np' not in voice.__dict__
    assert 'sf' not in voice.__dict__

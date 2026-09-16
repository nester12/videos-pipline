import json
from pathlib import Path
import pytest

from pipeline.writing.gemini import GeminiClient, extract_json_text
from pipeline.assets.scene_plan import build_scene_plan
from pipeline.writing.models import ScriptCandidate
from pipeline.publishing.package import build_caption, write_publish_package
from pipeline.publishing.tiktok import build_tiktok_init_payload
from pipeline.qa import validate_probe
from pipeline.render.ffmpeg_render import build_render_command
from pipeline.produce import select_topic
from pipeline.trends.models import TrendCandidate


def test_extract_json_text_from_gemini_response():
    data={'candidates':[{'content':{'parts':[{'text':'```json\n{"hooks": []}\n```'}]}}]}
    assert extract_json_text(data)=={'hooks':[]}


def test_gemini_client_refuses_unapproved_model():
    with pytest.raises(RuntimeError):
        GeminiClient('x', model='some-paid-model')


def test_gemini_client_retries_when_success_response_contains_malformed_json(monkeypatch):
    calls=[]

    class FakeResponse:
        status_code=200
        text=''
        def __init__(self, payload): self.payload=payload
        def json(self): return self.payload

    responses=[
        FakeResponse({'candidates':[{'content':{'parts':[{'text':'{"scripts":[{"text":"broken"}'}]}}]}),
        FakeResponse({'candidates':[{'content':{'parts':[{'text':'{"scripts": []}'}]}}]}),
    ]

    def fake_post(*args, **kwargs):
        calls.append(1)
        return responses.pop(0)

    monkeypatch.setattr('pipeline.writing.gemini.requests.post', fake_post)
    monkeypatch.setattr('pipeline.writing.gemini.time.sleep', lambda *_: None)

    result=GeminiClient('x').generate_json('prompt')
    assert result=={'scripts':[]}
    assert len(calls)==2


def test_scene_plan_breaks_script_into_multiple_beats():
    script=ScriptCandidate('This is the first point. Then something surprising happens. Finally the reason becomes clear.',90,'hook')
    beats=build_scene_plan(script, target_beats=3)
    assert len(beats) >= 3
    assert all(b.search_query for b in beats)


def test_build_caption_has_hook_and_small_hashtag_set():
    caption=build_caption('This changed overnight and almost nobody noticed.', ['ai','technology','news','fyp','viral','extra'])
    assert caption.startswith('This changed overnight')
    assert caption.count('#') <= 5


def test_publish_package_writes_metadata(tmp_path):
    video=tmp_path/'final.mp4'; video.write_bytes(b'fake')
    out=write_publish_package(str(video),'caption',{'topic':'AI'},str(tmp_path/'package'))
    assert (Path(out)/'caption.txt').read_text()=='caption'
    assert json.loads((Path(out)/'metadata.json').read_text())['topic']=='AI'


def test_tiktok_init_payload_is_official_pull_from_url_shape():
    payload=build_tiktok_init_payload('caption','https://cdn.example/video.mp4', privacy_level='SELF_ONLY')
    assert payload['source_info']['source']=='PULL_FROM_URL'
    assert payload['post_info']['privacy_level']=='SELF_ONLY'


def test_validate_probe_accepts_vertical_video():
    probe={'format':{'duration':'34.5'},'streams':[{'codec_type':'video','width':1080,'height':1920},{'codec_type':'audio'}]}
    assert validate_probe(probe,25,50)==[]


def test_validate_probe_flags_bad_ratio_and_audio():
    probe={'format':{'duration':'34.5'},'streams':[{'codec_type':'video','width':1920,'height':1080}]}
    errors=validate_probe(probe,25,50)
    assert any('9:16' in e for e in errors)
    assert any('audio' in e.lower() for e in errors)


def test_render_command_uses_vertical_dimensions():
    cmd=build_render_command(['a.mp4','b.mp4'],'narration.wav','final.mp4',duration=30)
    joined=' '.join(cmd)
    assert '1080:1920' in joined
    assert 'libx264' in joined


def test_select_topic_returns_highest_ranked_safe():
    items=[TrendCandidate('AI browser release','youtube',1,100,'technology'),TrendCandidate('old topic','youtube',.2,1,'internet')]
    chosen=select_topic(items, [], {'technology':1.2})
    assert chosen.title=='AI browser release'

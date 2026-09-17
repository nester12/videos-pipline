from pipeline.trends.google_trends import parse_google_rss
from pipeline.trends.youtube import parse_youtube_response
from pipeline.trends.scout import dedupe_trends
from pipeline.trends.models import TrendCandidate
from pipeline.safety.filter import is_safe_topic
from pipeline.ranking.topics import score_topic, rank_topics

RSS='''<rss xmlns:ht="https://trends.google.com/trending/rss"><channel><item><title>AI phone launch</title><ht:approx_traffic>20,000+</ht:approx_traffic><link>https://example.com/a</link></item></channel></rss>'''

def test_google_rss_normalizes_candidate():
    items = parse_google_rss(RSS, 'GB')
    assert items[0].title == 'AI phone launch'
    assert items[0].source == 'google_trends'
    assert items[0].velocity > 0


def test_youtube_response_normalizes_velocity():
    data={'items':[{'id':'x','snippet':{'title':'New AI feature','publishedAt':'2026-09-16T10:00:00Z','categoryId':'28'},'statistics':{'viewCount':'120000'}}]}
    items = parse_youtube_response(data, 'GB', now_iso='2026-09-16T12:00:00+00:00')
    assert items[0].source == 'youtube'
    assert items[0].velocity >= 50000


def test_youtube_trailer_is_not_misread_as_ai_because_trailer_contains_ai_letters():
    data={'items':[{'id':'x','snippet':{'title':'THE VVAAN - Official Trailer','publishedAt':'2026-09-16T10:00:00Z','categoryId':'24'},'statistics':{'viewCount':'120000'}}]}
    items = parse_youtube_response(data, 'GB', now_iso='2026-09-16T12:00:00+00:00')
    assert items[0].category == 'entertainment'


def test_niche_keyword_can_override_broad_youtube_entertainment_category():
    data={'items':[{'id':'x','snippet':{'title':'OpenAI launches a new browser feature','publishedAt':'2026-09-16T10:00:00Z','categoryId':'24'},'statistics':{'viewCount':'120000'}}]}
    items = parse_youtube_response(data, 'GB', now_iso='2026-09-16T12:00:00+00:00')
    assert items[0].category == 'technology'


def test_dedupe_prefers_higher_signal():
    a=TrendCandidate('AI phone launch','google_trends',0.8,10,'technology')
    b=TrendCandidate(' ai  phone launch ','youtube',0.9,20,'technology')
    out=dedupe_trends([a,b])
    assert len(out)==1 and out[0].source=='youtube'


def test_safety_filter_blocks_unsuitable_topic():
    ok, reason = is_safe_topic('unsafe restricted topic example')
    assert isinstance(ok, bool)


def test_score_penalizes_recent_topic():
    c=TrendCandidate('new ai browser','youtube',1.0,100,'technology')
    fresh=score_topic(c, [], {'technology':1.2})
    repeated=score_topic(c, ['New AI browser'], {'technology':1.2})
    assert repeated < fresh


def test_rank_keeps_safe_topic():
    safe=TrendCandidate('new AI browser','youtube',0.9,100,'technology')
    out=rank_topics([safe], [], {'technology':1.2})
    assert [x.title for x in out] == ['new AI browser']


def test_rank_excludes_categories_not_enabled_in_config():
    entertainment=TrendCandidate('Official movie trailer','youtube',1.0,999999,'entertainment')
    tech=TrendCandidate('New AI browser','youtube',0.8,100,'technology')
    out=rank_topics([entertainment, tech], [], {'technology':1.2, 'gaming':1.05, 'internet':1.1, 'story':0.9})
    assert [x.title for x in out] == ['New AI browser']

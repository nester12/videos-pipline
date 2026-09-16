from pipeline.trends.models import TrendCandidate
from pipeline.writing.gemini import GeminiClient
from pipeline.research.gdelt import normalize_articles, build_evidence_pack
from pipeline.writing.production import build_research_prompt


def test_gemini_defaults_to_current_free_flash_model():
    assert GeminiClient('x').model == 'gemini-3.6-flash'


def test_gdelt_articles_are_reduced_to_safe_evidence_fields():
    payload = {
        'articles': [
            {
                'title': 'Example technology story',
                'url': 'https://example.com/story',
                'domain': 'example.com',
                'seendate': '20260916T120000Z',
                'language': 'English',
                'sourcecountry': 'United Kingdom',
            }
        ]
    }
    articles = normalize_articles(payload)
    assert articles == [{
        'title': 'Example technology story',
        'url': 'https://example.com/story',
        'domain': 'example.com',
        'seen_date': '20260916T120000Z',
    }]


def test_research_prompt_uses_supplied_current_evidence_not_paid_grounding():
    topic = TrendCandidate('Example technology story', 'google_trends', 1.0, 1000, 'technology')
    evidence = build_evidence_pack(topic, [{
        'title': 'Example technology story',
        'url': 'https://example.com/story',
        'domain': 'example.com',
        'seen_date': '20260916T120000Z',
    }])
    prompt = build_research_prompt(topic, evidence)
    assert 'https://example.com/story' in prompt
    assert 'Use only the supplied evidence' in prompt

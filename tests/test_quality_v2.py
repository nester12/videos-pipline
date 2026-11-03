from motivation.backgrounds import relevance_score
from motivation.analysis import gemini_model


def test_footage_relevance():
    query = "gym athlete training"
    good = "athlete training with weights in a gym"
    bad = "woman massaging arm in a spa"
    assert relevance_score(good, query) > relevance_score(bad, query)
    assert relevance_score(bad, query) <= 0


def test_model_override(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3-flash")
    assert gemini_model() == "gemini-3-flash"

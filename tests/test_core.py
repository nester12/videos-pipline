import tempfile
from pathlib import Path
import pytest

from pipeline.cost_guard import assert_zero_cost_provider, require_env
from pipeline.config import load_config


def test_allows_only_known_zero_cost_providers():
    for provider in ['google_trends','youtube_free','gemini_free','pexels_free','kokoro_local','ffmpeg_local']:
        assert_zero_cost_provider(provider)
    with pytest.raises(RuntimeError):
        assert_zero_cost_provider('openai_paid')


def test_require_env_rejects_missing(monkeypatch):
    monkeypatch.delenv('MISSING_KEY', raising=False)
    with pytest.raises(RuntimeError):
        require_env('MISSING_KEY')


def test_load_config_yaml():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / 'c.yaml'
        p.write_text('regions:\n  - GB\nproduction:\n  target_seconds: 35\n', encoding='utf-8')
        cfg = load_config(str(p))
        assert cfg['regions'] == ['GB']
        assert cfg['production']['target_seconds'] == 35

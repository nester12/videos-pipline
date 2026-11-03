import os
import pytest
from motivation.quality import candidate_windows, best_window
from motivation.sources import relevance_score
from motivation.diagnostics import service_health
from motivation.common import PipelineError


def test_window_selects_end_of_thought():
    cues = [
        {'start': 0, 'end': 4, 'text': 'Every day is a chance to begin.'},
        {'start': 4, 'end': 9, 'text': 'Discipline is greater than motivation.'},
        {'start': 9, 'end': 17, 'text': 'Every failure teaches a powerful lesson.'},
        {'start': 17, 'end': 26, 'text': 'Remember how far you have already come.'},
        {'start': 26, 'end': 34, 'text': 'Take the next step today.'},
    ]
    candidates = candidate_windows(cues)
    assert candidates and all(c['end'] <= 34 for c in candidates)
    assert best_window(cues)['end'] >= best_window(cues)['start'] + 20


def test_short_speech_kept_together():
    cues = [{'start': 0, 'end': 12, 'text': 'Start now. You can do this.'}]
    assert best_window(cues)['end'] == 12


def test_title_ranking_prioritizes_speech_over_music():
    assert relevance_score('Motivational Speech for Discipline', 'motivational speech') > relevance_score('Speech Music Album DJ Mix', 'motivational speech')


def test_external_service_checks_skip_when_keys_missing(monkeypatch):
    for key in ('BUFFER_API_KEY', 'GEMINI_API_KEY', 'PEXELS_API_KEY', 'PIXABAY_API_KEY',
                'CLOUDINARY_CLOUD_NAME', 'CLOUDINARY_API_KEY', 'CLOUDINARY_API_SECRET', 'YOUTUBE_API_KEY'):
        monkeypatch.delenv(key, raising=False)
    status = service_health()
    assert status['Buffer']['status'] == 'skipped'
    assert status['Cloudinary']['status'] == 'skipped'

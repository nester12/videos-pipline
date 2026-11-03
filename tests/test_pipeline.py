from pathlib import Path
import wave
import pytest
from motivation.analysis import shift_cues
from motivation.common import PipelineError, stamp
from motivation.sources import accepted_license
from motivation.render import write_srt
from motivation.publish import validate_public_video_url, buffer_post


def test_license_allowlist():
    assert accepted_license("https://creativecommons.org/publicdomain/zero/1.0/")
    assert accepted_license("https://creativecommons.org/licenses/by/4.0/")
    assert not accepted_license("https://creativecommons.org/licenses/by-nc/4.0/")
    assert not accepted_license("")


def test_timestamp_rounding():
    assert stamp(61.123) == "00:01:01,123"
    assert stamp(-5) == "00:00:00,000"


def test_shift_cues():
    cues = [{"start": 10., "end": 11., "text": "Start"}, {"start": 12., "end": 13., "text": "End"}]
    result = shift_cues(cues, 10.5, 12.5)
    assert result[0]["start"] == 0
    assert result[1]["end"] == 2.0


def test_srt(tmp_path):
    p = write_srt([{"start": 0, "end": 1.5, "text": "Keep going"}], tmp_path / "demo.srt")
    assert "00:00:01,500" in p.read_text()


def test_public_url():
    validate_public_video_url("https://res.cloudinary.com/example/video/upload/video.mp4")
    with pytest.raises(PipelineError):
        validate_public_video_url("http://localhost/test.mp4")


def test_post_mode_is_safe_by_default():
    with pytest.raises(PipelineError):
        buffer_post("https://example.com/video.mp4", "channel", "x", "live")

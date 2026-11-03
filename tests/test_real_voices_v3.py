import pytest
from motivation.common import PipelineError
from motivation.cli import produce
from motivation.music_library import commons_track, select_music
from motivation.speaker import licensed_video

def test_original_ai_voice_is_disabled(tmp_path):
    with pytest.raises(PipelineError,match="AI generated voices are disabled"):
        produce(tmp_path,source="original")

def test_no_ai_fallback_if_archive_unavailable(tmp_path):
    with pytest.raises(PipelineError,match="needs internet"):
        produce(tmp_path,source="auto",offline=True)

def test_speaker_video_requires_reuse_rights(tmp_path):
    with pytest.raises(PipelineError,match="rights"):
        licensed_video("https://res.cloudinary.com/test/video/upload/speaker.mp4",tmp_path,rights_confirmed=False)

def test_reject_local_network_urls(tmp_path):
    with pytest.raises(PipelineError,match="Cloudinary"):
        licensed_video("https://localhost/private.mp4",tmp_path,rights_confirmed=True)

def test_external_music_requires_rights(tmp_path):
    with pytest.raises(PipelineError,match="music-rights-confirmed"):
        select_music(tmp_path,music_path="example.mp3")

def test_cc0_catalogue_rejects_noncommercial_track(monkeypatch,tmp_path):
    from motivation import music_library as m
    class MockResponse:
        def raise_for_status(self): pass
        def json(self):
            return {"query":{"pages":[{"imageinfo":[{"url":"https://upload.wikimedia.org/a.ogg",
                 "extmetadata":{"LicenseShortName":{"value":"CC BY-NC 4.0"},
                 "LicenseUrl":{"value":"https://creativecommons.org/licenses/by-nc/4.0/"}}}]}]}}
    monkeypatch.setattr(m.requests,"get",lambda *args,**kw:MockResponse())
    with pytest.raises(PipelineError,match="CC0"):
        commons_track("intense",tmp_path)

def test_cc0_music_download_records_provenance(monkeypatch,tmp_path):
    from motivation import music_library as m
    class MockResponse:
        def raise_for_status(self): pass
        def json(self):
            return {"query":{"pages":[{"imageinfo":[{"url":"https://upload.wikimedia.org/a.ogg",
                 "extmetadata":{"LicenseShortName":{"value":"CC0"},
                 "LicenseUrl":{"value":"https://creativecommons.org/publicdomain/zero/1.0/"}}}]}]}}
    monkeypatch.setattr(m.requests,"get",lambda *args,**kw:MockResponse())
    monkeypatch.setattr(m,"download",lambda url,path,max_mb:path.write_bytes(b"test sound") or path)
    monkeypatch.setattr(m,"duration",lambda path:200)
    result=commons_track("determined",tmp_path)
    assert result["license"].endswith("/zero/1.0/")
    assert result["type"]=="recorded instrumental"


def test_archive_source_does_not_auto_import_an_unused_speaker_url(tmp_path):
    with pytest.raises(PipelineError, match="needs internet"):
        produce(tmp_path, source="archive", offline=True,
                speaker_video_url="https://res.cloudinary.com/example/video/upload/speech.mp4")

def test_speaker_mode_gives_clear_permission_instructions(tmp_path):
    with pytest.raises(PipelineError, match="rights_confirmed"):
        produce(tmp_path, source="clip",
                speaker_video_url="https://res.cloudinary.com/example/video/upload/speech.mp4")

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



def test_archive_unknown_music_can_be_previewed_without_ai_or_classifier(monkeypatch, tmp_path):
    from motivation import discovery as d
    def fake_licensed(query, output, exclude=None):
        return {"identifier":"example123", "path":str(tmp_path/"speech.wav"),
                "origin":"https://archive.org/details/example123",
                "license":"https://creativecommons.org/licenses/by/4.0/",
                "reuse_requires_review":True}
    monkeypatch.setattr(d, "licensed_audio", fake_licensed)
    monkeypatch.setattr(d, "music_check", lambda p: {"status":"unknown"})
    monkeypatch.setattr(d, "transcribe", lambda p: [
        {"start":0.,"end":20.,"text":"Keep going today until you reach your goals."}])
    monkeypatch.setattr(d, "gemini_selection", lambda cues: {
        "start":0., "end":20., "score":7, "mood":"determined", "visual_query":"runner"})
    result=d.select_archive_recording("speech", tmp_path / "archive", allow_unknown_music=True, max_candidates=1)
    assert result["music_check"]["status"]=="unknown"
    assert "no" in result["music_check"]["soundtrack_policy"].lower()


def test_unknown_music_removes_added_soundtrack(monkeypatch, tmp_path):
    import motivation.cli as cli
    from pathlib import Path
    monkeypatch.setattr(cli, "licensed_video", lambda url, path, rights_confirmed: {
        "audio":tmp_path/"voice.wav", "video":tmp_path/"speaker.mp4",
        "source":{"origin":url, "license":"operator-confirmed", "reuse_requires_review":True}})
    monkeypatch.setattr(cli, "music_check", lambda audio: {"status":"unknown"})
    monkeypatch.setattr(cli, "transcribe", lambda audio: [
        {"start":0.,"end":18.,"text":"Keep going to build your future."}])
    monkeypatch.setattr(cli, "duration", lambda path: 18.0)
    monkeypatch.setattr(cli, "slice_audio", lambda *args: None)
    monkeypatch.setattr(cli, "write_srt", lambda cues, path: path)
    def fail_music(*args, **kwargs):
        raise AssertionError("A soundtrack must not be added to unknown audio")
    monkeypatch.setattr(cli, "select_music", fail_music)
    seen={}
    def fake_render(speech, background, captions, music, output, **kwargs):
        seen["music"]=music
        return output
    monkeypatch.setattr(cli, "render_video", fake_render)
    result=cli.produce(tmp_path / "out", preview=True, source="clip",
            speaker_video_url="https://res.cloudinary.com/sample/video/upload/example.mp4",
            rights_confirmed=True)
    assert seen["music"] is None
    assert result["soundtrack_added"] is False



def test_auto_discovered_archive_test_video_uploads_to_private_cloudinary(monkeypatch, tmp_path):
    import motivation.cli as cli
    monkeypatch.setattr(cli, "select_archive_recording", lambda *a, **kw: {
        "path": str(tmp_path / "recording.wav"),
        "cues": [{"start": 0., "end": 19., "text": "Keep going. Keep working."}],
        "selection": None, "music_check": {"status": "unknown"},
        "source": {"origin": "https://archive.org/details/test_speech", "license": "CC0",
                   "reuse_requires_review": True}
    })
    monkeypatch.setattr(cli, "duration", lambda path: 19.0)
    monkeypatch.setattr(cli, "slice_audio", lambda *a: None)
    monkeypatch.setattr(cli, "write_srt", lambda cues, path: path)
    monkeypatch.setattr(cli, "montage", lambda *a, **kw: {"path": tmp_path / "bg.mp4"})
    monkeypatch.setattr(cli, "render_video", lambda speech, bg, sub, music, out, **kw: out)
    seen = {}
    def fake_upload(video, *, authenticated_preview=False):
        seen["authenticated_preview"] = authenticated_preview
        return "https://res.cloudinary.com/test/video/authenticated/sample.mp4"
    monkeypatch.setattr(cli, "upload_cloudinary", fake_upload)
    result=cli.produce(tmp_path / "out", preview=True, source="archive", upload=True)
    assert seen["authenticated_preview"] is True
    assert result["cloudinary_delivery"] == "authenticated"
    assert result["cloudinary_folder"] == "motivation-test-previews"


def test_preview_cannot_publish_to_buffer(tmp_path):
    with pytest.raises(PipelineError, match="private Cloudinary previews"):
        produce(tmp_path, preview=True, source="archive", post="queue", channel_id="123")


def test_reject_audiobooks_when_searching_for_real_motivational_speeches():
    from motivation.sources import suitable_motivational_recording
    assert not suitable_motivational_recording({"title": "Your Invisible Power", "identifier": "your_invisible_power_2104_librivox"})
    assert not suitable_motivational_recording({"title": "Chapter 14 - Motivation", "identifier": "book_ch14"})
    assert suitable_motivational_recording({"title": "Discipline: motivational speech", "identifier": "speaker_123"})


def test_cinematic_montage_uses_multiple_shots_and_no_random_speaker(monkeypatch, tmp_path):
    from motivation import scenes as s
    from pathlib import Path
    seen=[]
    monkeypatch.setattr(s, "get_background", lambda q, dir: seen.append(q) or {
        "path":tmp_path/"stock.mp4", "source":"stock", "credit":"licensed"})
    monkeypatch.setattr(s, "run", lambda *args, **kwargs: None)
    result=s.montage("dramatic motivational speaker", tmp_path/"scenes",18.8,preview=True)
    assert result["scene_count"] >= 4
    assert all("speaker" not in x and "conference" not in x for x in seen)
    assert "B-roll" in result["style"]


def test_cinematic_montage_fails_instead_of_filler_when_no_licensed_clip(monkeypatch,tmp_path):
    from motivation import scenes as s
    monkeypatch.setattr(s, "get_background", lambda *a, **kw: None)
    with pytest.raises(PipelineError,match="No licensed cinematic footage"):
        s.montage("motivational speaker",tmp_path,18.8,preview=True)


def test_speech_quality_filter_disallows_generic_audiobook_ids():
    from motivation.sources import suitable_motivational_recording
    assert not suitable_motivational_recording({
        "title": "How to Win Friends and Influence People", "identifier": "book_librivox_123"})
    assert suitable_motivational_recording({
        "title": "Motivational talk on resilience", "identifier": "resilience_keynote_2026"})

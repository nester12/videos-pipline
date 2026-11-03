import json
import pytest
from motivation.publish import buffer_post, buffer_channels
from motivation.sources import accepted_license


def test_buffer_draft_payload(monkeypatch):
    import motivation.publish as p
    observed = {}
    def fake(query, variables):
        observed.update(variables)
        return {"createPost": {"post": {"id": "demo123"}}}
    monkeypatch.setattr(p, "buffer_request", fake)
    result = buffer_post("https://res.cloudinary.com/test/video/upload/example.mp4", "channel-1", "Test", "draft")
    assert result["id"] == "demo123"
    assert observed["input"]["saveToDraft"] is True
    assert observed["input"]["assets"][0]["video"]["url"].endswith(".mp4")


def test_buffer_queue_is_explicit(monkeypatch):
    import motivation.publish as p
    observed = {}
    def fake(query, variables):
        observed.update(variables)
        return {"createPost": {"post": {"id": "queued"}}}
    monkeypatch.setattr(p, "buffer_request", fake)
    buffer_post("https://res.cloudinary.com/test/video/upload/example.mp4", "channel-1", "Test", "queue")
    assert observed["input"]["saveToDraft"] is False


def test_buffer_channels_queries(monkeypatch):
    import motivation.publish as p
    def fake(query, variables=None):
        if 'account' in query:
            return {"account": {"organizations": [{"id": "org-1", "name": "Demo"}]}}
        return {"channels": [{"id": "channel-1", "name": "My TikTok", "service": "tiktok"}]}
    monkeypatch.setattr(p, "buffer_request", fake)
    assert buffer_channels()[0]["organization"] == "Demo"



def test_cloudinary_private_preview_upload_uses_authenticated_delivery(monkeypatch, tmp_path):
    import cloudinary
    import cloudinary.uploader
    from motivation.publish import upload_cloudinary
    for key, value in (("CLOUDINARY_CLOUD_NAME", "sample"),
                       ("CLOUDINARY_API_KEY", "key"),
                       ("CLOUDINARY_API_SECRET", "secret")):
        monkeypatch.setenv(key, value)
    seen = {}
    monkeypatch.setattr(cloudinary, "config", lambda **kwargs: seen.update({"configured": True}))
    def fake_upload(filename, **kwargs):
        seen.update(kwargs)
        return {"type": kwargs.get("type", "upload"),
                "secure_url": "https://res.cloudinary.com/sample/video/authenticated/motivation-test-previews/test.mp4"}
    monkeypatch.setattr(cloudinary.uploader, "upload", fake_upload)
    url = upload_cloudinary(tmp_path / "sample.mp4", authenticated_preview=True)
    assert seen["type"] == "authenticated"
    assert seen["folder"] == "motivation-test-previews"
    assert "/authenticated/" in url


def test_cloudinary_rejects_private_preview_without_proof_of_authentication(monkeypatch, tmp_path):
    import cloudinary
    import cloudinary.uploader
    from motivation.publish import upload_cloudinary
    for key in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"):
        monkeypatch.setenv(key, "test")
    monkeypatch.setattr(cloudinary, "config", lambda **kwargs: None)
    monkeypatch.setattr(cloudinary.uploader, "upload", lambda *a, **kw: {
        "type": "upload",
        "secure_url": "https://res.cloudinary.com/test/video/upload/open.mp4"})
    with pytest.raises(Exception, match="authenticated"):
        upload_cloudinary(tmp_path / "sample.mp4", authenticated_preview=True)

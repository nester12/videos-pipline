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

"""Cloudinary upload + Buffer GraphQL, with no accidental live posts."""
from __future__ import annotations
import os
import requests
from pathlib import Path
from urllib.parse import urlparse
from .common import PipelineError

BUFFER_ENDPOINT = "https://api.buffer.com"


def upload_cloudinary(path: Path) -> str:
    import cloudinary
    import cloudinary.uploader
    keys = ["CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"]
    if any(not os.getenv(x) for x in keys):
        raise PipelineError("Cloudinary credentials missing")
    cloudinary.config(cloud_name=os.environ[keys[0]], api_key=os.environ[keys[1]],
                      api_secret=os.environ[keys[2]], secure=True)
    result = cloudinary.uploader.upload(str(path), resource_type="video", folder="motivation-prototype",
                                         overwrite=False)
    url = result.get("secure_url", "")
    validate_public_video_url(url)
    return url


def validate_public_video_url(url: str):
    p = urlparse(url)
    if p.scheme != "https" or not p.netloc or not p.path.lower().endswith((".mp4", ".mov")):
        raise PipelineError("Buffer video requires direct public HTTPS MP4/MOV URL")


def buffer_request(query: str, variables: dict | None = None) -> dict:
    key = os.getenv("BUFFER_API_KEY") or os.getenv("Buffer_API_KEY")
    if not key:
        raise PipelineError("BUFFER_API_KEY missing")
    res = requests.post(BUFFER_ENDPOINT, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                        json={"query": query, "variables": variables or {}}, timeout=35)
    res.raise_for_status()
    data = res.json()
    if data.get("errors"):
        raise PipelineError("Buffer GraphQL error: " + str([e.get("message") for e in data["errors"]]))
    return data.get("data") or {}


def buffer_channels() -> list[dict]:
    data = buffer_request("query { account { organizations { id name } } }")
    channels = []
    for org in data.get("account", {}).get("organizations", []):
        result = buffer_request("query ($id: OrganizationId!) { channels(input: { organizationId: $id }) { id name displayName service } }",
                                {"id": org["id"]})
        for item in result.get("channels", []):
            item["organization"] = org.get("name", "")
            channels.append(item)
    return channels


def buffer_post(video_url: str, channel_id: str, text: str, mode="draft") -> dict:
    """draft or queue. Never send to queue without explicit mode='queue'."""
    if mode not in ("draft", "queue"):
        raise PipelineError("Unsupported posting mode")
    if not channel_id.strip():
        raise PipelineError("Select a Buffer channel ID, no automatic posting to an arbitrary channel")
    validate_public_video_url(video_url)
    query = """mutation CreateVideo($input: CreatePostInput!) {
        createPost(input: $input) {
          ... on PostActionSuccess { post { id text dueAt } }
          ... on MutationError { message }
        }
    }"""
    payload = {"text": text, "channelId": channel_id, "schedulingType": "automatic", "mode": "addToQueue",
               "assets": [{"video": {"url": video_url, "metadata": {"thumbnailOffset": 2000}}}],
               "saveToDraft": mode == "draft", "aiAssisted": True}
    result = buffer_request(query, {"input": payload}).get("createPost") or {}
    if "message" in result:
        raise PipelineError("Buffer rejected video: " + str(result["message"]))
    if not result.get("post", {}).get("id"):
        raise PipelineError("Buffer did not confirm a created post")
    return result["post"]

# Zero-Cost TikTok Pipeline V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working £0-cost pipeline that discovers timely topics, ranks them, creates multiple hooks/scripts with a free Gemini path, sources free Pexels footage, renders a vertical short locally, runs QA, and exports a publish package while laying the foundation for TikTok OAuth and performance learning.

**Architecture:** A modular Python package under `src/` with clear stages for trend discovery, ranking/safety, writing, asset search, rendering, publishing state, and analytics. GitHub Actions runs scheduled discovery and production jobs. Any paid fallback is forbidden; missing free quota causes a clean skip.

**Tech Stack:** Python 3.11, requests, feedparser, PyYAML, pytest, FFmpeg, Pillow, Kokoro TTS (production runner), optional openai-whisper for alignment, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-16-zero-cost-tiktok-growth-pipeline-design.md`

## Global Constraints

- £0 hard budget. No paid API, paid model, paid hosting, paid runner, subscription, or automatic paid fallback.
- API keys/tokens only through environment variables / GitHub Actions secrets.
- No TikTok password storage or browser automation.
- Public automated TikTok posting only through official TikTok scopes/approval.
- Original content only; no copied creator scripts.
- Safety filter blocks dangerous challenges, self-harm, weapons, drugs, gambling, and explicit sexual content.
- If a free quota is exhausted, skip or retry later rather than bill.

---

### Task 1: Core configuration and cost guard

**Files:**
- Create: `src/pipeline/config.py`
- Create: `src/pipeline/cost_guard.py`
- Create: `config/pipeline.yaml`
- Create: `tests/test_cost_guard.py`
- Create: `tests/test_config.py`
- Create: `requirements.txt`

**Interfaces:**
- Produces: `load_config(path: str) -> dict`
- Produces: `assert_zero_cost_provider(provider: str) -> None`
- Produces: `require_env(name: str) -> str`

- [ ] Write tests asserting allowed providers are `google_trends`, `youtube_free`, `gemini_free`, `pexels_free`, `kokoro_local`, `ffmpeg_local`, and that any provider containing paid/billing model identifiers raises `RuntimeError`.
- [ ] Run `pytest tests/test_cost_guard.py tests/test_config.py -v` and verify failure before implementation.
- [ ] Implement the minimal config loader and guard.
- [ ] Re-run tests and commit.

### Task 2: Trend discovery and normalization

**Files:**
- Create: `src/pipeline/trends/google_trends.py`
- Create: `src/pipeline/trends/youtube.py`
- Create: `src/pipeline/trends/models.py`
- Create: `src/pipeline/trends/scout.py`
- Create: `tests/test_trends.py`

**Interfaces:**
- `TrendCandidate(title: str, source: str, freshness: float, velocity: float, category: str, source_url: str = "")`
- `fetch_google_trends(region: str) -> list[TrendCandidate]`
- `fetch_youtube_trends(api_key: str, region: str) -> list[TrendCandidate]`
- `collect_trends(config: dict) -> list[TrendCandidate]`

- [ ] Add fixture-driven tests for RSS normalization and YouTube API normalization.
- [ ] Verify tests fail.
- [ ] Implement Google Trends RSS parsing and optional YouTube API retrieval with timeouts and no paid fallback.
- [ ] Deduplicate candidates by normalized title.
- [ ] Re-run tests and commit.

### Task 3: Safety and topic ranking

**Files:**
- Create: `src/pipeline/safety/filter.py`
- Create: `src/pipeline/ranking/topics.py`
- Create: `tests/test_ranking.py`
- Create: `tests/test_safety.py`

**Interfaces:**
- `is_safe_topic(text: str) -> tuple[bool, str]`
- `score_topic(candidate: TrendCandidate, recent_topics: list[str], category_weights: dict[str, float]) -> float`
- `rank_topics(...) -> list[TrendCandidate]`

- [ ] Write tests for blocked categories and repetition penalties.
- [ ] Verify failure.
- [ ] Implement deterministic scoring using freshness, velocity, category fit, visual potential proxy, and repetition penalty.
- [ ] Re-run tests and commit.

### Task 4: Hook/script tournament using Gemini free tier

**Files:**
- Create: `src/pipeline/writing/gemini.py`
- Create: `src/pipeline/writing/tournament.py`
- Create: `src/pipeline/writing/models.py`
- Create: `tests/test_tournament.py`

**Interfaces:**
- `GeminiClient.generate_json(prompt: str, schema_name: str) -> dict`
- `run_hook_tournament(topic: TrendCandidate, research: dict, client: GeminiClient, count: int = 6) -> list[HookCandidate]`
- `run_script_tournament(..., count: int = 3) -> ScriptCandidate`

- [ ] Add mocked tests that verify multiple hooks/scripts are generated and low-scoring candidates are rejected.
- [ ] Verify failure.
- [ ] Implement REST-based Gemini calls using only an explicitly configured free-tier model name and bounded retries for 429/5xx.
- [ ] Add deterministic local scoring fallback for parsing/validation only, never a paid AI fallback.
- [ ] Re-run tests and commit.

### Task 5: Scene plan and Pexels asset engine

**Files:**
- Create: `src/pipeline/assets/pexels.py`
- Create: `src/pipeline/assets/scene_plan.py`
- Create: `tests/test_assets.py`

**Interfaces:**
- `build_scene_plan(script: ScriptCandidate) -> list[SceneBeat]`
- `search_pexels_videos(query: str, api_key: str, per_page: int = 8) -> list[VideoAsset]`
- `choose_assets(beats: list[SceneBeat], recent_urls: set[str], api_key: str) -> list[VideoAsset]`

- [ ] Add mocked tests for portrait preference, minimum resolution, and repetition avoidance.
- [ ] Verify failure.
- [ ] Implement Pexels search/download metadata with attribution retained.
- [ ] Re-run tests and commit.

### Task 6: Local audio, renderer, and QA

**Files:**
- Create: `src/pipeline/audio/voice.py`
- Create: `src/pipeline/render/ffmpeg_render.py`
- Create: `src/pipeline/render/captions.py`
- Create: `src/pipeline/qa.py`
- Create: `tests/test_captions.py`
- Create: `tests/test_qa.py`

**Interfaces:**
- `synthesize_kokoro(text: str, output_path: str, voice: str) -> str`
- `segment_captions(text: str, max_words: int = 5) -> list[str]`
- `render_short(scene_files: list[str], narration_path: str, captions: list[dict], output_path: str) -> str`
- `validate_video(path: str, expected_min_s: float, expected_max_s: float) -> list[str]`

- [ ] Write caption and QA tests first.
- [ ] Implement grouped caption segmentation and FFmpeg command construction.
- [ ] Keep Kokoro loaded only in production runtime; tests mock it.
- [ ] Validate dimensions, duration, audio stream, and decodeability with ffprobe.
- [ ] Re-run tests and commit.

### Task 7: End-to-end production orchestration and export package

**Files:**
- Create: `src/pipeline/produce.py`
- Create: `src/pipeline/publishing/package.py`
- Create: `tests/test_produce.py`

**Interfaces:**
- `produce_one(config: dict) -> ProductionResult`
- `write_publish_package(video_path: str, caption: str, metadata: dict, out_dir: str) -> str`

- [ ] Add an integration test using mocked network/TTS/render calls.
- [ ] Verify failure.
- [ ] Implement stage-by-stage orchestration with a reason code on skip/failure.
- [ ] Export `final.mp4`, `caption.txt`, and `metadata.json` as one publish directory.
- [ ] Re-run tests and commit.

### Task 8: TikTok OAuth/publisher scaffold and performance learner

**Files:**
- Create: `src/pipeline/publishing/tiktok.py`
- Create: `src/pipeline/learning/store.py`
- Create: `src/pipeline/learning/weights.py`
- Create: `tests/test_learning.py`
- Create: `tests/test_tiktok_payloads.py`

**Interfaces:**
- `build_tiktok_upload_request(...) -> dict`
- `record_post_metrics(db_path: str, row: dict) -> None`
- `derive_category_weights(db_path: str) -> dict[str, float]`

- [ ] Test official payload generation without posting.
- [ ] Test SQLite metric storage and bounded weight updates.
- [ ] Implement only official TikTok API request construction; no credential collection in code.
- [ ] Implement account-relative learning weights with sensible min/max bounds.
- [ ] Re-run tests and commit.

### Task 9: GitHub Actions and documentation

**Files:**
- Create: `.github/workflows/tests.yml`
- Create: `.github/workflows/trend-scout.yml`
- Create: `.github/workflows/produce.yml`
- Create: `.github/workflows/learn.yml`
- Create: `README.md`
- Create: `.gitignore`

**Interfaces:**
- Scheduled workflows call `python -m pipeline.trends.scout`, `python -m pipeline.produce`, and the learning entry point.

- [ ] Add CI workflow for pytest on Python 3.11.
- [ ] Add scheduled trend and production workflows using only standard hosted runners.
- [ ] Add artifact upload for export-only videos.
- [ ] Document required secrets: `GEMINI_API_KEY`, `PEXELS_API_KEY`, optional `YOUTUBE_API_KEY`, and later TikTok OAuth secrets.
- [ ] Document zero-cost behavior and quota exhaustion behavior.
- [ ] Run all tests and commit.

### Task 10: Final verification

**Files:** none expected.

- [ ] Run `pytest -q` and require zero failures.
- [ ] Run `python -m compileall src` and require success.
- [ ] Inspect workflows for any paid runner/model/service configuration.
- [ ] Inspect repository for committed secrets.
- [ ] Open a PR from `build/zero-cost-pipeline-v1` to `main` with verification evidence.

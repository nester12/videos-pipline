# Zero-Cost TikTok Growth Pipeline — Design

Date: 2026-09-16
Repository: `nester12/videos-pipline`
Status: Proposed design approved in chat; implementation has not started.

## 1. Goal

Build a fully automated short-form video pipeline designed to improve reach, retention, likes, shares, and follower conversion while keeping the user's direct operating cost at exactly £0.

The system must not claim or depend on a guaranteed follower outcome. It will instead maximize controllable factors: topic freshness, hook quality, watch-time structure, visual pacing, originality, posting consistency, and learning from real post performance.

## 2. Hard Constraints

1. **£0 hard budget.** No paid API, paid model, paid hosting, paid runner, subscription, or automatic paid fallback is allowed.
2. If a free quota is exhausted, the relevant job must pause or degrade to another free/local path. It must never switch to billing.
3. Use only standard GitHub-hosted runners in this public repository. Do not use larger paid runners.
4. API keys and tokens must live in GitHub Actions secrets and must never be committed.
5. TikTok access must use official OAuth/developer authorization. Do not store the user's TikTok password.
6. Public fully automated TikTok posting will only be enabled if TikTok grants the required posting scope/audit approval. Until then, the pipeline may generate and prepare uploads using the official supported flow without bypassing TikTok restrictions.
7. Generated content must be original and must avoid copying creator scripts or copyrighted narration.
8. Trend filtering must block dangerous challenges, self-harm, weapons, drugs, gambling, explicit sexual content, and other unsuitable material.

## 3. High-Level Strategy

The old pipeline is primarily a generator. The new system will be an adaptive decision system:

`Trend discovery -> candidate scoring -> research -> hook competition -> script competition -> quality gate -> scene plan -> assets -> voice -> edit -> QA -> publish/export -> performance collection -> learning -> next run`

The pipeline should post fewer stronger videos rather than maximize raw quantity. Initial target: 2-3 production videos per day, with configuration allowing later changes based on measured performance.

## 4. Architecture

### 4.1 Trend Scout

Purpose: discover what is rising now rather than generating from a fixed topic list.

Free sources:
- Google Trends Trending Now / RSS where available.
- YouTube Data API v3 using its free default quota.
- Pexels search is not a trend source; it is only an asset source.
- TikTok account performance data is used to learn which trend families work for this account.

Output: `data/trends.json`

Each candidate stores:
- title/topic
- source
- timestamp
- region
- freshness
- search/video velocity proxies
- category
- safety status
- evidence URLs/IDs where available

### 4.2 Topic Ranker

Purpose: avoid chasing every trend.

A deterministic score combines:
- freshness
- growth/velocity signal
- relevance to the account's winning categories
- visual availability
- originality opportunity
- expected short-form clarity
- recent-topic repetition penalty
- prior account performance for similar topics

The first release will use explainable weighted scoring. Later weights can be adjusted automatically from post results.

### 4.3 Research Pack Builder

Purpose: give the writer facts and context without copying source wording.

For the top topic candidates, collect small factual summaries from permitted public sources/APIs. Store structured facts, not full copied articles or creator transcripts.

Output per topic:
`data/research/<topic_id>.json`

### 4.4 Hook Tournament

Purpose: stop accepting the first hook an LLM produces.

For each selected topic:
1. Generate 5-8 hook candidates.
2. Score each hook for curiosity, immediate clarity, specificity, novelty, emotional tension, and whether the payoff can honestly satisfy the promise.
3. Reject clickbait that the script cannot pay off.
4. Keep the best 2-3 hooks.

The scoring pass must be separate from the generation pass to reduce self-selection bias.

### 4.5 Script Tournament

Generate multiple scripts around the strongest hooks. Scripts should generally target 25-50 seconds initially, because the new system must test concise videos instead of defaulting to ~90 seconds.

Each script is scored for:
- first 2 seconds
- information/story density
- escalation every few seconds
- concrete details
- clarity when heard without visuals
- payoff strength
- dead-space risk
- originality
- factual consistency with the research pack
- suitability for available visuals

Only the top script passes to production. A minimum score is required; if every candidate is weak, the topic is skipped instead of publishing filler.

### 4.6 Scene Planner

Convert the winning script into 2-5 second visual beats.

Each beat specifies:
- narration segment
- search keywords
- ideal clip type
- motion/crop instruction
- caption emphasis
- optional transition or punch-in

The planner should deliberately change visual context frequently enough to prevent a static-background feel while avoiding chaotic cuts.

### 4.7 Asset Engine

Primary source: Pexels API free tier.

Rules:
- use video assets with valid Pexels attribution/licensing requirements
- cache downloaded assets during the workflow
- avoid exact clip repetition in recent posts
- prefer portrait footage; otherwise crop intelligently
- reject low-resolution or unsuitable clips
- allow a local repository/user-supplied asset pool as a second free source

No paid stock fallback is allowed.

### 4.8 Voice Engine

Default: local Kokoro TTS on the GitHub runner.

Requirements:
- one consistent voice identity initially
- natural punctuation-aware delivery
- configurable speed
- loudness normalization through FFmpeg
- no paid TTS dependency

Word/segment alignment uses a local speech alignment path such as Whisper when necessary.

### 4.9 Editor / Renderer

Use FFmpeg/Python locally.

Initial edit style:
- 1080x1920 vertical
- scene changes based on the scene plan
- readable grouped captions rather than single-word-only captions
- highlight important words selectively
- dynamic crop/punch-in where useful
- hook text treatment in opening seconds
- light transitions only when they support pacing
- normalized narration loudness
- no copyrighted music dependency

The renderer should support style variants so future performance data can compare caption and pacing treatments.

### 4.10 Automated Quality Gate

Before publication/export, validate:
- file exists and decodes
- 9:16 dimensions
- expected duration
- narration is audible
- no excessive silence
- captions cover the intended narration
- no black frames/empty asset segments
- no missing attribution metadata
- no duplicate script hash
- no recently repeated asset sequence
- content safety checks pass

If QA fails, do not publish.

### 4.11 Publishing Layer

TikTok integration must use official developer APIs and OAuth.

Modes:
1. `export_only` — always supported; produces a finished MP4 + caption package.
2. `tiktok_upload` — use the official upload flow when the user's app/account authorization supports it.
3. `tiktok_direct_post` — only after the TikTok application has the required `video.publish` access/audit and the account has authorized it.

No browser automation, password storage, or policy bypassing.

### 4.12 Performance Learner

After posts have had time to accumulate data, ingest available official metrics for the user's own videos, including fields such as views, likes, comments, and shares when the authorized API exposes them.

Store:
- topic/category
- hook family
- script length
- video duration
- caption style
- scene cut rate
- posting time
- views
- likes
- comments
- shares
- derived engagement rates
- follower delta when an official authorized endpoint makes it available

Output: `data/performance.sqlite`

The learner updates preference weights, not the model itself. Example: if shorter AI-news explainers repeatedly outperform generic story videos, the ranker allocates more future slots to that pattern.

## 5. Free AI Strategy

### Primary
Gemini API on a free-tier project for structured research synthesis, hooks, scripts, critique, and scene plans.

### Free fallback
Use another explicitly free configured provider only if it can be verified to have a non-billing mode at implementation time. Otherwise use local heuristics or skip the job.

### Billing guard
The code must not contain any billing setup or paid model fallback. Quota/rate-limit errors trigger exponential backoff, then a clean skip.

## 6. Scheduled Workflows

### `trend-scout.yml`
Runs several times per day.
- collect trend candidates
- score/filter them
- update trend cache

### `produce.yml`
Runs 2-3 production slots per day.
- choose highest-quality unused opportunity
- build research pack
- run hook/script tournament
- create scene plan
- obtain assets
- synthesize voice
- render
- QA
- publish/export

### `learn.yml`
Runs daily.
- fetch performance for known published posts
- calculate normalized performance
- update topic/hook/style preferences

### `tests.yml`
Runs on pushes/PRs.
- unit tests
- deterministic fixture tests
- renderer smoke test
- no-secret checks

## 7. State and Data

Persistent small state may be committed as JSON when safe, but performance history should prefer SQLite persisted through a repository-safe mechanism or compact exported summaries.

Never commit OAuth tokens, API keys, personal identifiers, or account credentials.

Suggested structure:

```text
.github/workflows/
  trend-scout.yml
  produce.yml
  learn.yml
  tests.yml
src/
  config.py
  trends/
  research/
  ranking/
  writing/
  assets/
  audio/
  render/
  publishing/
  learning/
  safety/
tests/
data/
  trends.json
  recent_topics.json
  recent_assets.json
config/
  pipeline.yaml
docs/
```

## 8. Configuration

`config/pipeline.yaml` controls behavior without code changes:
- regions
- allowed content categories
- production slots
- target duration ranges
- hook count
- script count
- minimum quality score
- caption style
- recent-topic cooldown
- asset repetition cooldown
- posting mode

Default categories should remain focused enough to build an audience identity instead of becoming a random trend account.

## 9. Error Handling

- All network calls use timeouts and bounded retries.
- 429/quota errors do not crash unrelated workflow stages.
- If Gemini is unavailable, skip generation rather than pay.
- If Pexels has no good asset, use the approved local asset pool or skip the topic.
- If TikTok publishing fails, retain the finished package and mark it pending; do not regenerate the same video.
- Every stage emits machine-readable logs and a human-readable summary.
- Failed items retain a reason code for later diagnosis.

## 10. Testing

Unit tests:
- trend normalization
- ranking weights
- repetition detection
- hook/script score parsing
- API response parsing
- caption segmentation
- cost guard
- safety filter
- publishing state transitions

Integration tests with fixtures/mocks:
- trend -> ranked topic
- topic -> script package
- scene plan -> asset requests
- render smoke test using tiny fixtures
- publish payload generation without actually posting

Production checks:
- manual workflow dispatch for one dry-run video
- export-only mode first
- TikTok OAuth only after local/dry-run tests pass

## 11. Success Measurement

The system will optimize for account-relative improvement, not promise a fixed follower number.

Primary metrics:
- median views per post
- median watch/retention metrics when accessible
- share rate
- like rate
- comment rate
- follower conversion when accessible
- percentage of videos exceeding the account's rolling median

Evaluation should compare rolling windows, because a single viral or failed video is noisy.

## 12. Security and Account Access

The user should never send a TikTok password in chat or commit it to GitHub.

TikTok authorization flow:
1. create/configure a TikTok developer app
2. obtain the app Client Key/Client Secret
3. store app credentials in GitHub Actions secrets
4. authorize the user's TikTok account through TikTok OAuth
5. store refresh/access tokens only as secrets or another secure supported mechanism
6. request only the scopes required for posting and own-account analytics

## 13. Initial External Credentials

Required for the strongest first release:
- `GEMINI_API_KEY` — Gemini free tier
- `PEXELS_API_KEY` — Pexels API
- `YOUTUBE_API_KEY` — YouTube Data API v3 free quota

TikTok integration later requires:
- `TIKTOK_CLIENT_KEY`
- `TIKTOK_CLIENT_SECRET`
- OAuth-generated user tokens/scopes

No paid service is required by design.

## 14. Rollout

Phase 1: trend discovery, tournaments, asset engine, local TTS, renderer, QA, export-only.

Phase 2: TikTok OAuth and supported upload/direct-post path.

Phase 3: automatic performance ingestion and adaptive ranking weights.

Phase 4: controlled A/B-style experiments across duration, hook family, edit pacing, and caption style.

Each phase must remain usable at £0 before the next phase is added.

## 15. Non-Goals

- guaranteeing 100,000 followers or any fixed growth result
- purchasing followers/views/engagement
- spam posting
- copying viral creators word-for-word
- bypassing TikTok API approval or posting restrictions
- using paid AI/video-generation services
- generating expensive cinematic AI video when free licensed footage and editing can achieve the goal more reliably

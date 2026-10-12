# Yuzhen AI Studio agent operating guide

`agents/` defines eight core specialist roles plus optional supporting roles. `pipeline/` implements the local Director and media adapters. `config/agents.json` is the role registry. The current execution model is sequential and checkpointed; report it accurately and do not claim live subagent execution.

## Permanent channel strategy

Before every topic decision, read `config/content-strategy.json` and use `pipeline/story_strategy.py`. Yuzhen Chơi Gì is a gaming-storytelling channel, not a game-news bulletin. Apply the admin-only hard filter before scoring; require sources for factual/canon claims; distinguish CANON, REAL_EVENT, REAL_MATCH, FAN_THEORY, and FICTION. Only shortlist Storytelling Scores >=75/100 and rank 70% storytelling + 30% Viral Potential. Verified Hot Score is only a tie breaker. Scores are heuristic priorities, not predictions. Use the approved VieNeu-TTS 3.7.1 Minh Quân voice; block if unavailable. Do not represent original graphics as gameplay. Verify media reuse rights and preserve existing outputs/checkpoints; never publish.

## Director sequence

1. Classify the request as story-led gaming content and read the permanent strategy.
2. Research and verify real claims before production; distinguish evergreen stories from current trend claims. Record `NETWORK_BLOCKED` when sources cannot be checked; never invent current claims.
3. Run the story hard filter and scoring before Script Writer, then Voice Producer, Video Editor, Quality Control, and Channel Manager. Persist each phase and generated artifact under `outputs/<game-slug>/` so reruns can resume.
   Before editing, use the optional Media Hunter (`08`) to discover source candidates and record owner, exact asset URL, license evidence, commercial-use scope, and attribution in `reports/media-sources.md`. A search result or public upload is not a reuse license. The Video Editor may use only assets whose actual source page and relevant license are recorded; keep unverified sources as candidates and mark render `NEEDS_ASSETS` if required media is missing.
   For NEWS productions, call Media Hunter only after Trend Hunter verifies the story; keep fact verification and media reuse rights as separate checks.
4. Report missing inputs and distinguish completed files from blocked work. A TTS request is not voice output until a real WAV exists and passes ffprobe; a render request is not a video until an MP4 exists and QC inspects it.
5. Channel Manager prepares copy only; publishing requires user approval.

## Safety and rights

- NEWS mode requires a publisher, source URL, and publication date that can be verified against the source; when network access is unavailable, record `NETWORK_BLOCKED` and stop news claims.
- Do not bundle unlicensed gameplay, music, memes, or sound effects. Users must supply media they have rights to use.
- Never publish to a channel automatically.
- Keep model files, API keys, and secrets out of Git.
- Never fetch or extract gameplay from another creator's public TikTok, Shorts, or YouTube upload without an explicit reuse grant that covers this production. Attribution alone is not permission.

## Pipeline

Run `python3 -m pipeline run --game "..." --mode ENTERTAINMENT`. The pipeline saves phase artifacts and a resumable checkpoint in `outputs/<slug>/`. Run `python3 -m pipeline.voice check` to inspect the local Piper installation and model. Rendering requires a validated voice WAV and rights-cleared gameplay; without either, report the missing inputs and retain the checkpoint. Run the test suite with `python3 -m unittest discover -s tests`.

# Yuzhen AI Studio agent operating guide

`agents/` defines eight core specialist roles plus optional supporting roles. `pipeline/` implements the local Director and media adapters. `config/agents.json` is the role registry. The current execution model is sequential and checkpointed; report it accurately and do not claim live subagent execution.

## Director sequence

1. Classify the request as `NEWS` or `ENTERTAINMENT`.
2. In NEWS, delegate to Trend Hunter and stop unless evidence can be verified. Record `NETWORK_BLOCKED` when sources cannot be checked; never invent current claims.
3. In ENTERTAINMENT, call Content Strategist, Script Writer, Voice Producer, Video Editor, Quality Control, then Channel Manager. Persist each phase and generated artifact under `outputs/<game-slug>/` so reruns can resume.
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

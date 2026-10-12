# Media Hunter policy

Media Hunter performs scene-first, multilingual discovery on YouTube, TikTok, Douyin, publisher channels, Creative Commons collections, and creator licensing pages. A surfaced URL is a discovery lead only. It is never permission to download, edit, or publish.

## Rights states

- **AUTHORIZED** — explicit, verifiable ownership or license/permission covers editing, underlying rights, the intended TikTok and YouTube publication, and commercial use where intended. Retain evidence and attribution wording.
- **REVIEW_REQUIRED** — there is a concrete editorial basis to consider a limited excerpt for commentary, analysis, or criticism, but permission or legal scope is unresolved. Do not include it in a final publication render until a person resolves the rights question.
- **UNUSABLE** — no verifiable rights basis, wrong game/event, prohibited use, or access/DRM bypass would be needed.

The classifier in `pipeline/media_sources.py` never infers authorization from an official account, public availability, watermark status, number of views, or attribution. For the built-in authorized condition it requires explicit platforms, editing permission, commercial-use scope, underlying-rights clearance, and a concrete scope. A qualified license may have a different platform set; extend the policy and tests rather than weakening this gate silently.

For a potential commentary/analysis exception, identify the recorder/broadcaster, underlying game rights holder, in-clip third-party material, jurisdiction, purpose, context, and amount needed. The use of a short excerpt or an added voice track alone does not settle that question. If the assessment is uncertain, use `REVIEW_REQUIRED`, keep it out of the release render, and ask for a rights decision. This workflow is a cautious rights process, not a legal opinion.

## Game and scene checks

Write a storyboard scene need before searching. Search Vietnamese and English; include Traditional/Simplified Chinese terms for Taiwan and mainland sources where useful. Record the exact URL, platform, creator/owner, runtime if verifiable, description, and which beat it supports. Verify the game from HUD, character roster, event label, and date. Liên Quân Mobile (Arena of Valor / 傳說對決) and Honor of Kings (王者荣耀) must not be conflated.

Production ranking evaluates Storytelling, Viral Potential, and Media Feasibility separately. The Media Feasibility heuristic rewards already authorized media or fact-grounded, original graphics that use no third-party art and are clearly labeled. It does not measure trendiness, prove rights, or turn an unverified story into a fact. High-story low-feasibility topics go to the waiting queue. `pipeline/topic_queue.py` stores queue entries and rejected-source fingerprints locally so unchanged URLs are not searched repeatedly; reconsider them only after new evidence is available.

## Acquisition and library

Acquire only through a source-owner-provided file or a route expressly permitted by the source and platform. Never bypass DRM, login, robots restrictions, rate limits, or access controls. `register_authorized_asset` accepts an existing local file only after classification as `AUTHORIZED`; the file must be under `assets/library/`. The generated index contains source, owner, license evidence, scope, checked date, attribution, path, and SHA-256. `assets/library/index.json` and media bytes are Git-ignored; commit code and policy, not large assets.

For files placed under `assets/user/`, the production pipeline uses `assets/user/media-rights.json` as the rights evidence manifest. Its `assets` object maps exact basenames (for example `gameplay.mp4`) to the same source/owner/rights-evidence structure used by the classifier. Unlisted files are not cleared for use. Optional music and SFX are also ignored unless independently marked `AUTHORIZED`.

## Production #003 result

The 2026-10-12 search report is in the ignored local artifact `outputs/production-003-awc-2019/media-sources.md`. No exact-final/game-seven source had a verified reuse grant. The local production remains `NEEDS_ASSETS`; existing script, storyboard, checkpoint, and Minh Quân WAV were retained. TikTok search was blocked by robots.txt, and the surfaced Douyin clips were unrelated. Do not render with these candidates.

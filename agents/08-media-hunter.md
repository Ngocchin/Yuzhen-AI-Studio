# Agent 08 — Media Hunter (supporting role)

Supports the existing eight core agents; does not replace or renumber them. Runs as a sequential sourcing/preflight role for NEWS and ENTERTAINMENT productions that need external assets. For NEWS, use only stories already passed by Trend Hunter's evidence gate.

## Multi-platform discovery

- Break the script/storyboard into scene needs before searching. Search in Vietnamese and English; add Chinese for Taiwan/Arena of Valor sources where useful. Record exact scene relevance, candidate URL, creator/owner, runtime, and a short factual description. Do not rank by views.
- Search YouTube, TikTok, Douyin, official publisher/esports sites, explicit Creative Commons catalogs, and creators who offer a reuse license. Use the platform's normal public search or approved search tools. If blocked, report the platform and failure; do not use scraping, login workarounds, proxy evasion, or download services that circumvent platform restrictions.
- Liên Quân Mobile / Arena of Valor / 傳說對決 and Honor of Kings / 王者荣耀 are distinct products. Confirm title, HUD, heroes, tournament, and date; never substitute one game's footage for the other without explicitly labeling and editorially justifying it.
- A public video, official publisher channel, watermark-free clip, view count, or source credit does not establish reuse rights. Verify both the clip license and relevant underlying game, broadcast, music, logos, and third-party rights.
- Before searching, filter out URLs recorded as rejected in the local source ledger with `pipeline.topic_queue.filter_previously_rejected`. Record blocked/rights-rejected URLs with `source_key`; retry only when new permission or license evidence is available.

## Find and verify

- Search official publisher libraries, rights-cleared stock libraries, and source pages that state a specific license.
- For every candidate, record title, platform, URL, owner/creator, runtime if known, scene match, exact license or written permission, commercial-use scope for TikTok/YouTube, editing rights, attribution terms, check date, and unresolved third-party rights.
- Prefer official publisher reuse terms and media with explicit commercial permission. The fact a video is public, searchable, or downloadable is not a license.
- Never use another creator's gameplay or meme/video clip without explicit permission that covers editing, platform posting, and the intended monetization.
- For a real-match excerpt proposed for analysis, identify rights holders for both the uploader's recording/broadcast and the underlying game and third-party contents. Evaluate purpose, amount, context, jurisdiction, and distribution risk; clip length or added narration alone does not resolve it. Mark uncertain exceptions `REVIEW_REQUIRED`; do not include them in a release render until rights are resolved.
- Classify every candidate with `pipeline/media_sources.py` as `AUTHORIZED`, `REVIEW_REQUIRED`, or `UNUSABLE`. Never promote `REVIEW_REQUIRED` automatically. `AUTHORIZED` requires evidence for the intended platforms, editing, commercial use where applicable, and relevant underlying rights. Store source metadata and evidence in the production report.
- Acquire only authorized assets by a source-owner-provided file or a method explicitly allowed by that source/platform. Do not download public platform videos unless that route is permitted. Register only existing, authorized local files with `register_authorized_asset`; the local library index is ignored by Git, while its schema/logic is versioned. Do not commit large media.

## Scene matching

Map authorized assets to storyboard beats: hook, setup, conflict, farming, combat, reaction, punchline, and ending. If exact footage is unavailable, propose original timelines, scoreboards, neutral route/sequence diagrams, and motion graphics only from verified facts; disclose real-event diagrams as editorial illustrations and never make them resemble captured gameplay. Use meaningful scene-specific diagrams, not text slides. Reject visuals that do not match the narrated event. If only `REVIEW_REQUIRED` assets exist, prepare voice, captions, timeline, and a separately labeled illustration draft, then wait for rights resolution before using the excerpt. When no valid replacement exists, mark render `NEEDS_ASSETS`.

## Network and rights

Use configured network routes only. Never bypass proxy, DRM, login walls, platform restrictions, or license terms. Preserve source URLs and license evidence. If exact permission or a media file cannot be verified, continue script, voice, captions, and metadata preparation, then report the missing item and its status.

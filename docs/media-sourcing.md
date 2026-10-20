# Media Hunter and creator-led rights policy

Media Hunter finds multiple source candidates for individual storyboard scenes. Its job is to support a new, authored story, not compile unrelated highlights or reupload a creator's work. Each used segment must support a specific line of original narration, analysis, criticism, or reaction. Record both the clip's source and its underlying game, broadcast, music, and third-party rights holders where relevant.

The persistent classifier policy is `config/media-rights-policy.json`; the executable classifier is `pipeline/media_sources.py`. The categories below are rights pathways, not a single automated legal conclusion.

## Rights categories

- **LICENSED_OR_PERMITTED** — a verifiable license, permission, ownership record, or publisher policy covers the requested edit, target platform(s), and commercial scope when planned. Rights to gameplay capture, broadcast, music, overlays, and other included material may belong to different parties; record those separately.
- **PLATFORM_REMIX** — an owner-enabled native feature such as Stitch, Duet, or platform Remix may be used only through that feature, inside its current product rules and account settings. It does not authorize downloading a file, rendering it locally, or cross-posting it to another service.
- **COPYRIGHT_EXCEPTION_CANDIDATE** — a specific segment has an articulated criticism, analysis, commentary, or other exception rationale. Store the actual scene and narration mapping, jurisdiction, acquisition basis, amount needed, market implications, factors supporting the argument, and factors against it. Candidate status is not a legal decision or a promise of monetization. A scoped human assessment is required before the production gate clears it.
- **UNUSABLE** — a source is prohibited, obtained through bypass of a restriction, materially mismatched, unidentified, or has no viable recorded basis for this production. If new permission, a valid license, or a substantive exception assessment appears, create/update the evidence and reclassify; do not repeatedly search the same unchanged URL.

The software does not set a duration-based safe harbor. Clip length, source credit, an official uploader, a watermark, or added voiceover does not automatically resolve copyright. The classifier is an evidence and workflow aid, not legal advice. Copyright rules vary by jurisdiction; never assume a U.S. fair-use analysis applies in Vietnam or another territory.

### Exception-candidate assessment fields

For each candidate clip, record:

- the precise criticism/analysis purpose and how the excerpt supports that claim;
- a storyboard scene ID, the actual commentary line, and the analytical function of that segment;
- the source, uploader/recorder, broadcast owner, game/publisher, music, and other material rights holders as far as known;
- lawful access/retrieval basis, jurisdiction, planned platforms, and commercial intent;
- why the amount and context are appropriate to the point being made, without using an arbitrary seconds limit;
- market/substitution concerns and other adverse factors, as well as facts that may support the case;
- a human assessment record, reviewer, scope, platform list, commercial scope, date, and expiry if a legal assessment clears a use.

Missing facts remain explicitly unknown. A renderer may use an exception candidate only when a human assessment record is scoped to that edit/platform/commercial purpose, a lawful retrieval path is documented, the source is in the private library, the exact scene mapping exists, and technical game/timecode checks pass. The pipeline never declares that a use is lawful.

## Story and scene workflow

1. Keep the eight core agents and the approved VieNeu-TTS 3.7.1 Minh Quân preset. Media strategy does not switch voices.
2. Break the authored story into scenes and create several targeted multilingual search queries per scene. Use only permitted public search routes; if a platform blocks search, report that and do not circumvent it.
3. Record URL, creator/owner, title, platform, exact scene relevance, asset/game identity, runtime/resolution only when checked, and timecode only after actually viewing a lawfully accessible copy.
4. Do not conflate Liên Quân Mobile / Arena of Valor / 傳說對決 with Honor of Kings / 王者荣耀.
5. Develop a meaningful original angle and map every selected clip to an original voice line. Do not copy a creator's script, narration, distinctive sequence, or edit pattern.
6. Use FFmpeg only with locally available clips for which the acquisition and production pathway is documented. Native remix-only sources remain within the platform and cannot enter a local FFmpeg edit.
7. If footage is insufficient, preserve script/voice/checkpoints and emit an edit decision list with candidate URLs, unknown timecodes, scene mapping, and exact rights decision needed. `REAL_FOOTAGE_FIRST` does not fall back to vector scenes or generated gameplay.

## Monetization review

Record separate assessments for YouTube and TikTok. YouTube reused-content review concerns the channel's original contribution and is separate from copyright clearance or Content ID claims. TikTok's Creator Rewards rules, including originality, length, region/account eligibility, change over time and must be rechecked; sponsorship/affiliate disclosures and music licensing are separate. A video may be lawful to post yet ineligible for a platform program, or have a license yet still attract an automated claim. Never promise monetization approval.

## Acquisition and library

Never bypass DRM, login walls, robots rules, proxy/network policy, rate limits, or platform restrictions. Store media in Git-ignored `assets/media-library/` only when the recorded route is allowed. `register_authorized_asset` requires operational clearance and an existing local file. Do not commit large media, downloaded candidate footage, or credentials.

## Production #004 — Volkath and Tel'Annas

Use `outputs/production-004-real-footage/` for the separate real-footage assessment. Prior script, research, checkpoint, Minh Quân voice and illustrative MP4 under `outputs/production-004/` are preserved. Previously discovered URLs are tracked in `outputs/media-source-ledger.json`; do not repeat those searches without new evidence. Candidate video metadata was not frame-verified, so do not invent scene timecodes or treat possible matches as usable footage.

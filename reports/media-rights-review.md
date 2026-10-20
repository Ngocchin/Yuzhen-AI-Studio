# Media rights review — Production #004

**As of 2026-10-13 · Result: NEEDS_ASSETS.** I reviewed the existing 16 candidates and did not repeat searches of rejected URLs. There are no locally acquired clips, verified timecodes, or assets cleared for this production. Existing script, checkpoint, prior render and Minh Quân WAV remain untouched. The YouTube watch pages were not inspectable in this environment; three accessible Bilibili pages exposed page metadata and an anti-repost notice, but not video frames. A platform uploader is not automatically the video’s original owner, and neither uploader rights nor Garena/Tencent game rights establish the other.

## Candidate ranking

| Rank | Asset / source | Fit and observed evidence | Rights / acquisition | Status |
|---|---|---|---|---|
| 1 | `bili-volkath-cinematic` — [AOV Volkath cinematic](https://www.bilibili.tv/video/2043948997) | Page title names AoV/Volkath cinematic; uploader shown as `bili_1517568386`. Page: 20 views, Apr 16 2022. Frames, duration, source origin, and arrow event not verified. | Page says repost prohibited without creator permission. Underlying game/footage ownership unknown. | EXCEPTION_REVIEW; WAITING_FOR_RIGHTS_REVIEW |
| 2 | `yt-garena-volkath-2019` — [Volkath 2019 trailer](https://www.youtube.com/watch?v=rE3OmMNs9WM) | Existing discovery record says official Garena Liên Quân introduction; exact content cannot be verified because watch page unavailable. | Official publisher upload is not a reuse license. No clip permission, edit scope, or download route recorded. | UNKNOWN; WAITING_FOR_RIGHTS_REVIEW |
| 3 | `bili-volkath-pro-gameplay` — [Volkath pro gameplay](https://www.bilibili.tv/en/video/2047207342) | Page title suggests character gameplay; uploader `Chris Nero`, page shows 73 views, Premium, Aug 3 2022. No frames or event/timecode verified; gameplay may not illustrate the lore claim. | Page says repost prohibited without creator permission; creator, game, soundtrack and any embedded material rights are unresolved. | EXCEPTION_REVIEW; WAITING_FOR_RIGHTS_REVIEW |
| 4 | `yt-telannas-gameplay` — [Tel’Annas gameplay](https://www.youtube.com/watch?v=PwTDpP3d2_U) | Search metadata only; creator and exact content unverified. Potentially relevant only to Tel’Annas scene. | No license, owner verification, or permitted retrieval route. | UNKNOWN; WAITING_FOR_RIGHTS_REVIEW |
| 5 | `bili-telannas-spotlight` — [Tel’Annas Hero Spotlight](https://www.bilibili.tv/video/2048186169) | Page title suggests hero spotlight; uploader shown as `bili_1898507244` (not verified as owner). Page displays repost prohibition. No frames, game build, or scene verified. | No permission from uploader or publisher; likely source relationship is unknown. | EXCEPTION_REVIEW; WAITING_FOR_RIGHTS_REVIEW |

The Bilibili repost warning is a platform page notice, not proof that the uploader is or is not the original owner. Do not describe these as confirmed reuploads.

## Deep review: three accessible page records

1. **Volkath cinematic (Bilibili 2043948997):** page metadata title/uploader/date and repost notice observed; no actual footage, duration, timecodes, ownership chain, or game build verified. Likely candidates for hook/setup only, conditional on lawful review copy and frame match.
2. **Volkath gameplay (Bilibili 2047207342):** page metadata title/uploader/date and repost notice observed; no gameplay action, sound/music, duration, or timecodes verified. It may not evidence the lore event; scene fit remains weak.
3. **Tel’Annas spotlight (Bilibili 2048186169):** title/uploader/date and repost notice observed; no frames/timecodes verified and no evidence that this is the original publisher asset. Could at most be considered for a Tel’Annas visual, after source and rights verification.

All three lack a lawful local acquisition method and a source file. No FFprobe or SHA-256 can be reported for remote candidates. The exact machine-readable per-asset evidence and six-scene narration mapping are in [`assets/media-library/index.json`](../assets/media-library/index.json) and [`outputs/production-004-real-footage/edit-decision-list.json`](../outputs/production-004-real-footage/edit-decision-list.json).

## Existing 16 URL disposition

The prior assessment counts 0 LICENSED_OR_PERMITTED, 0 PLATFORM_REMIX, 11 COPYRIGHT_EXCEPTION_CANDIDATE and 5 UNUSABLE. EXCEPTION_REVIEW candidates remain unresolved, not approved. The five recorded unusable/mismatch entries are `yt-garena-volkath-skin-trailer`, `yt-garena-volkath-selection`, `yt-garena-telannas-tulen`, `yt-garena-telannas-fox`, and `bili-volkath-shogun`; the source records mark these as prohibited/mismatched or skin-specific. No new evidence was found to reverse those decisions.

## What is needed for intake

A user can attach an original file in a new Codex task (paperclip / file attachment), without using a terminal. Include the source URL, title, uploader, who supplied the file, and the applicable license/permission text or a record from the rights holder. For broadcast footage include broadcaster rights; for embedded music include music rights; state whether edited organic monetized posts, affiliate/sponsorship, paid ads, TikTok and YouTube are covered. A public URL alone is not enough. I can then import the attached file to the Cloud task workspace, probe it with FFprobe, compute SHA-256, and register it in the media library if its scope is cleared. The current configuration has no durable external storage attached, so task-local imported files may need reattachment in later Cloud tasks.

# Media intake for Codex Cloud

Users do not need a terminal to provide review media.

1. Attach the original video/audio in the Codex task using the file attachment control. Include its source URL/title and identify who supplied it.
2. Paste the rights evidence or attach it too: permission/license, permitted platforms, edits, monetized organic posts, affiliate/sponsorship/paid-ad scope, attribution and expiry. Identify separate broadcaster/game/music rights where present. A public link or credit is not a rights grant.
3. Ask Yuzhen to import the attached file. The task can copy the attachment into `assets/media-library/`, inspect it with FFprobe and SHA-256, then add it to the cleared `assets` index only after evidence covers the requested use. Attachments are not downloaded from third-party URLs by this workflow.
4. For later Cloud tasks, reattach the file unless a durable storage connector has been configured. The current project has no durable external media storage configured. Large media stays outside Git.

If only a URL is supplied, Yuzhen can keep a candidate record and scene proposal, but must not fetch through DRM, login walls, or prohibited means. An exception review must be scoped to the actual clip, purpose, jurisdiction, acquisition method and commercial context; user acceptance of risk does not itself authorize use.

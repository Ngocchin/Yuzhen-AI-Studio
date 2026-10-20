"""Scene-level, rights-gated planning for real-footage-first productions.

This module never downloads platform media and never substitutes generated
graphics. It validates candidate records and decides whether verified local
clips may enter SAFE or INTERNAL_REVIEW edits.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from pipeline.media_sources import classify_source

ROOT = Path(__file__).resolve().parents[1]
LIBRARY_ROOT = ROOT / "assets/media-library"
MODES = {"SAFE", "INTERNAL_REVIEW"}
GAME_ALIASES = {
    "lien quan mobile": "arena of valor",
    "arena of valor": "arena of valor",
    "aov": "arena of valor",
    "rov": "arena of valor",
    "传说对决": "arena of valor",
    "傳說對決": "arena of valor",
    "honor of kings": "honor of kings",
    "王者荣耀": "honor of kings",
}


def normalize_game(value: str) -> str:
    return GAME_ALIASES.get((value or "").strip().casefold(), (value or "").strip().casefold())


def _probe(path: Path) -> dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return {"verified": False, "reason": "ffprobe is unavailable"}
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height", "-of", "json", str(path)],
        capture_output=True, text=True,
    )
    try:
        data = json.loads(result.stdout)
        duration = float(data.get("format", {}).get("duration", 0))
    except (ValueError, json.JSONDecodeError):
        return {"verified": False, "reason": result.stderr.strip() or "ffprobe could not read the media"}
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    return {
        "verified": result.returncode == 0 and video is not None and duration > 0,
        "duration_seconds": duration,
        "width": video.get("width") if video else None,
        "height": video.get("height") if video else None,
        "reason": result.stderr.strip() if result.returncode else "",
    }


def _internal_review_permitted(candidate: dict) -> tuple[bool, str]:
    evidence = candidate.get("internal_review_evidence") or {}
    if candidate.get("acquisition_bypassed_controls") is True:
        return False, "The clip was acquired by bypassing access controls."
    required = ("retrieval_permitted", "internal_use_permitted", "evidence_record")
    if not all(evidence.get(key) for key in required):
        return False, "No evidence documents that retrieval and internal draft use are permitted."
    if evidence.get("retrieval_permitted") is not True or evidence.get("internal_use_permitted") is not True:
        return False, "The supplied evidence does not permit both retrieval and internal use."
    return True, "Retrieval and internal-use evidence is recorded; publication rights remain unresolved."


def _scene_match(candidate: dict, scene_id: str, expected_game: str) -> dict | None:
    if normalize_game(candidate.get("game", "")) != normalize_game(expected_game):
        return None
    if normalize_game(candidate.get("game", "")) == "honor of kings" and normalize_game(expected_game) != "honor of kings":
        return None
    for match in candidate.get("scene_matches", []):
        if str(match.get("scene_id")) != str(scene_id):
            continue
        start, end = match.get("in_seconds"), match.get("out_seconds")
        if start is None and end is None:
            return match
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or start < 0 or end <= start:
            continue
        duration = candidate.get("duration_seconds")
        if isinstance(duration, (int, float)) and end > duration:
            continue
        return match
    return None


def preflight_real_footage(
    scenes: list[dict], candidates: list[dict], *, mode: str = "SAFE",
    production_dir: Path | str | None = None, expected_game: str = "Arena of Valor",
) -> dict:
    """Build a scene plan; only verified, permitted local files qualify for edit."""
    mode = mode.upper()
    if mode not in MODES:
        raise ValueError(f"mode must be one of {sorted(MODES)}")
    production_dir = Path(production_dir or ROOT)
    rows, covered = [], set()
    for scene in scenes:
        scene_id = str(scene.get("id", scene.get("scene_id", "")))
        scene_rows = []
        for candidate in candidates:
            match = _scene_match(candidate, scene_id, expected_game)
            if match is None:
                continue
            rights = classify_source(candidate)
            local = candidate.get("local_path")
            media_path = (production_dir / local).resolve() if local else None
            in_library = media_path is not None and LIBRARY_ROOT.resolve() in media_path.parents
            media_probe = _probe(media_path) if in_library and media_path.is_file() else {"verified": False, "reason": "No local authorized library file"}
            has_timecode = isinstance(match.get("in_seconds"), (int, float)) and isinstance(match.get("out_seconds"), (int, float))
            eligible = (rights["status"] == "AUTHORIZED" and in_library and media_probe["verified"]
                        and has_timecode
                        and candidate.get("game_identity_verified") is True)
            exception = candidate.get("copyright_exception") or {}
            if rights["category"] == "COPYRIGHT_EXCEPTION_CANDIDATE":
                mappings = exception.get("commentary_map") or []
                scene_mapping = any(
                    isinstance(item, dict)
                    and str(item.get("scene_id")) == scene_id
                    and bool(item.get("commentary_text"))
                    and bool(item.get("analysis_function"))
                    for item in mappings
                )
                eligible = eligible and scene_mapping and rights["operationally_cleared"]
            internal_ok, internal_reason = _internal_review_permitted(candidate)
            if (mode == "INTERNAL_REVIEW" and rights["category"] != "PLATFORM_REMIX"
                    and rights["status"] == "REVIEW_REQUIRED" and internal_ok):
                eligible = (in_library and media_probe["verified"] and has_timecode
                            and candidate.get("game_identity_verified") is True)
            row = {
                "scene_id": scene_id,
                "narration": scene.get("narration", scene.get("text", "")),
                "candidate_id": candidate.get("asset_id") or candidate.get("candidate_id"),
                "title": candidate.get("title"),
                "creator": candidate.get("creator") or candidate.get("owner"),
                "platform": candidate.get("platform"),
                "url": candidate.get("source_url"),
                "duration_seconds": candidate.get("duration_seconds"),
                "resolution": candidate.get("resolution"),
                "timecode": ({"in_seconds": match["in_seconds"], "out_seconds": match["out_seconds"]}
                             if has_timecode else None),
                "rights_status": rights["status"],
                "rights_category": rights["category"],
                "rights_reason": rights["reason"],
                "rights_supporting_factors": rights.get("supporting_factors", []),
                "rights_opposing_factors": rights.get("opposing_factors", []),
                "internal_review_basis": internal_reason,
                "game_identity_verified": candidate.get("game_identity_verified") is True,
                "confidence": match.get("confidence", "LOW"),
                "editorial_match": match.get("editorial_match", ""),
                "local_file_probe": media_probe,
                "eligible_for_edit": eligible,
            }
            scene_rows.append(row)
            if eligible:
                covered.add(scene_id)
        rows.extend(scene_rows or [{
            "scene_id": scene_id,
            "narration": scene.get("narration", scene.get("text", "")),
            "candidate_id": None, "url": None, "timecode": None,
            "rights_status": None, "confidence": "NONE",
            "eligible_for_edit": False, "missing_reason": "No verified, scene-matched candidate record.",
        }])
    missing = [str(scene.get("id", scene.get("scene_id", ""))) for scene in scenes if str(scene.get("id", scene.get("scene_id", ""))) not in covered]
    ready = bool(scenes) and not missing
    status = ("READY_FOR_PUBLICATION_REVIEW" if mode == "SAFE" else "READY_FOR_INTERNAL_REVIEW") if ready else "NEEDS_FOOTAGE_RIGHTS"
    return {
        "mode": mode,
        "expected_game": expected_game,
        "status": status,
        "may_render": ready,
        "generated_graphics_fallback": False,
        "scene_matches": rows,
        "missing_scene_ids": missing,
        "note": "Search discovery is not a license. Review required remains excluded unless retrieval and internal-use evidence are explicitly recorded.",
    }

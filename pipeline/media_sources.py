"""Evidence-based rights classification and private media-library registry.

This module records source evidence; it is not a legal decision engine. In
particular, a copyright-exception candidate stays a candidate until a scoped,
human legal assessment is recorded. Clip duration is never a decision rule.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
LIBRARY_ROOT = ROOT / "assets/media-library"
INDEX_PATH = LIBRARY_ROOT / "index.json"
RIGHTS_CONFIG = ROOT / "config/media-rights-policy.json"
RIGHTS_CATEGORIES = {
    "LICENSED_OR_PERMITTED",
    "PLATFORM_REMIX",
    "COPYRIGHT_EXCEPTION_CANDIDATE",
    "UNUSABLE",
}


def _http_url(value: str) -> bool:
    parsed = urlparse(value or "")
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _unexpired(value: str | None) -> tuple[bool, str]:
    if not value:
        return True, ""
    try:
        expiry = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
    except ValueError:
        return False, "License expiry is malformed and needs verification."
    if expiry <= datetime.now(timezone.utc):
        return False, "The recorded permission or assessment has expired."
    return True, ""


def classify_rights(
    source: dict,
    *,
    target_platforms: tuple[str, ...] = ("youtube", "tiktok"),
    commercial_use: bool = True,
    commercial_context: str = "creator_monetization",
) -> dict:
    """Classify a source and report evidence/risk without making a legal finding.

    LICENSED_OR_PERMITTED is only an operational clearance when explicit proof
    covers all requested platforms, editing, commercial use (when requested),
    and relevant underlying rights. PLATFORM_REMIX is valid only inside the
    named platform feature and is never permission to download/cross-post.
    COPYRIGHT_EXCEPTION_CANDIDATE requires a clip-specific editorial rationale;
    only a scoped human legal assessment can clear it for the requested output.
    """
    if not isinstance(source, dict):
        raise TypeError("source must be a dict")
    evidence = source.get("rights_evidence") or {}
    owner = source.get("owner") or source.get("creator")
    source_url = source.get("source_url", "")

    if (evidence.get("revoked") is True or evidence.get("prohibited") is True or evidence.get("drm_or_access_bypass_required") is True
            or source.get("acquisition_bypassed_controls") is True or source.get("editorial_unsuitable") is True):
        reason = ("Recorded permission was revoked." if evidence.get("revoked") is True else
                  "Asset is editorially unsuitable for this story." if source.get("editorial_unsuitable") is True else
                  "Use is prohibited or would require bypassing access controls/DRM.")
        return {
            "category": "UNUSABLE", "status": "UNUSABLE", "operationally_cleared": False,
            "reason": reason,
            "supporting_factors": [], "opposing_factors": [reason],
            "review_required": False,
        }
    if not _http_url(source_url) or not owner or not source.get("title"):
        return {
            "category": "UNUSABLE", "status": "UNUSABLE", "operationally_cleared": False,
            "reason": "Source URL, source identity, or title is missing; this record is not usable as a production source.",
            "supporting_factors": [], "opposing_factors": ["Source cannot be reliably identified."],
            "review_required": False,
        }

    valid_expiry, expiry_reason = _unexpired(evidence.get("expires_at"))
    if not valid_expiry and evidence.get("expires_at"):
        return {
            "category": "UNUSABLE" if "expired" in expiry_reason else "UNUSABLE",
            "status": "UNUSABLE", "operationally_cleared": False,
            "reason": expiry_reason, "supporting_factors": [],
            "opposing_factors": ["Permission validity is expired or cannot be verified."],
            "review_required": True,
        }

    basis = str(evidence.get("basis", "")).strip()
    permitted = set(evidence.get("permitted_platforms") or [])
    rights_holders_cleared = evidence.get("underlying_rights_cleared") is True
    if source.get("broadcast_footage") is True or source.get("footage_type") in {"broadcast", "esports_broadcast", "live_broadcast"}:
        rights_holders_cleared = rights_holders_cleared and evidence.get("broadcaster_rights_cleared") is True
    if source.get("contains_music") is True:
        rights_holders_cleared = rights_holders_cleared and evidence.get("music_rights_cleared") is True
    if commercial_context not in {"creator_monetization", "organic_post"}:
        rights_holders_cleared = rights_holders_cleared and commercial_context in set(evidence.get("permitted_commercial_contexts") or [])
    licensed = (
        basis in {"user_ownership", "written_permission", "license", "publisher_policy"}
        and (basis == "user_ownership" or _http_url(evidence.get("license_url", "")) or bool(evidence.get("permission_record")))
        and (basis != "license" or evidence.get("license_verified") is True)
        and set(target_platforms).issubset(permitted)
        and evidence.get("editing_allowed") is True
        and rights_holders_cleared
        and bool(evidence.get("scope"))
        and (evidence.get("attribution_required") is not True or bool(evidence.get("attribution_text") or source.get("attribution")))
        and (not commercial_use or evidence.get("commercial_use") is True)
    )
    if licensed:
        return {
            "category": "LICENSED_OR_PERMITTED", "status": "AUTHORIZED",
            "operationally_cleared": True,
            "reason": "Recorded permission covers requested platforms, editing, relevant rights holders, and the requested commercial context.",
            "supporting_factors": ["Explicit license/permission basis", "Scope and target platforms recorded", "Editing and underlying rights recorded"],
            "opposing_factors": [], "review_required": False,
            "target_platforms": list(target_platforms), "commercial_use": commercial_use,
            "commercial_context": commercial_context,
        }

    remix = evidence.get("platform_remix") or {}
    if (
        remix.get("enabled_by_owner") is True
        and remix.get("feature") in {"duet", "stitch", "remix"}
        and remix.get("platform") in target_platforms
        and remix.get("native_feature_only") is True
        and bool(remix.get("verification_record"))
    ):
        return {
            "category": "PLATFORM_REMIX", "status": "REVIEW_REQUIRED",
            "operationally_cleared": False, "native_feature_only": True,
            "permitted_platform": remix["platform"], "feature": remix["feature"],
            "reason": "Owner-enabled native remix may be available only inside the recorded platform feature; it does not authorize a local download, FFmpeg import, or cross-post.",
            "supporting_factors": ["Owner-enabled native feature is recorded"],
            "opposing_factors": ["Cross-platform and offline-render rights are not established."],
            "review_required": True,
        }

    exception = source.get("copyright_exception") or {}
    supporting = list(exception.get("supporting_factors") or [])
    opposing = list(exception.get("opposing_factors") or [])
    commentary_map_valid = (
        isinstance(exception.get("commentary_map"), list)
        and bool(exception["commentary_map"])
        and all(isinstance(item, dict) and item.get("scene_id") is not None
                and item.get("commentary_text") and item.get("analysis_function")
                for item in exception["commentary_map"])
    )
    case_is_documented = (
        bool(exception.get("editorial_purpose"))
        and bool(exception.get("identified_rights_holders"))
        and commentary_map_valid
        and bool(exception.get("source_acquisition_basis"))
        and bool(exception.get("jurisdiction"))
        and bool(exception.get("amount_rationale"))
        and bool(exception.get("market_effect_analysis"))
        and bool(supporting) and bool(opposing)
    )
    if case_is_documented:
        assessment = exception.get("legal_assessment") or {}
        assessment_covers = (
            commentary_map_valid
            and assessment.get("outcome") == "approved_for_intended_use"
            and bool(assessment.get("assessment_record"))
            and bool(assessment.get("reviewer"))
            and bool(assessment.get("jurisdiction"))
            and assessment.get("jurisdiction") == exception.get("jurisdiction")
            and assessment.get("rights_holders_reviewed") is True
            and set(target_platforms).issubset(set(assessment.get("platforms") or []))
            and (not commercial_use or assessment.get("commercial_use") is True)
            and (commercial_context in {"creator_monetization", "organic_post"}
                 or commercial_context in set(assessment.get("permitted_commercial_contexts") or []))
            and bool(assessment.get("scope"))
            and exception.get("source_access_legitimate") is True
        )
        if assessment.get("expires_at"):
            assessment_covers = assessment_covers and _unexpired(assessment.get("expires_at"))[0]
        return {
            "category": "COPYRIGHT_EXCEPTION_CANDIDATE", "status": "AUTHORIZED" if assessment_covers else "REVIEW_REQUIRED",
            "operationally_cleared": bool(assessment_covers),
            "legal_assessment_recorded": bool(assessment_covers),
            "reason": ("Scoped human assessment and lawful acquisition basis are recorded for this use; this software does not determine legality." if assessment_covers else "Documented commentary/analysis may support an exception argument, but a scoped assessment and lawful acquisition basis are not both recorded."),
            "supporting_factors": supporting, "opposing_factors": opposing,
            "review_required": not assessment_covers,
            "target_platforms": list(target_platforms), "commercial_use": commercial_use,
            "jurisdiction": exception.get("jurisdiction"),
            "duration_is_not_a_rule": True,
        }

    # A source with unresolved rights is not promoted based on being public,
    # short, credited, or paired with voiceover. It may be reclassified when
    # permission or a substantive, clip-specific exception assessment is added.
    return {
        "category": "UNUSABLE", "status": "UNUSABLE", "operationally_cleared": False,
        "reason": str(evidence.get("review_basis") or "No applicable license, native remix basis, or documented clip-specific exception case is recorded for this production."),
        "supporting_factors": [],
        "opposing_factors": ["Reuse scope is not documented", "Platform rules and underlying-game/broadcast rights may differ"],
        "review_required": True,
    }


def classify_source(source: dict) -> dict:
    """Compatibility API for existing pipeline gates.

    Legacy AUTHORIZED means the new policy found an operational clearance;
    documented but unresolved native-remix and exception cases stay
    REVIEW_REQUIRED; a record with no plausible basis remains UNUSABLE.
    """
    result = classify_rights(source)
    if result["category"] == "COPYRIGHT_EXCEPTION_CANDIDATE" and not result["operationally_cleared"]:
        legacy = "REVIEW_REQUIRED"
    elif result["operationally_cleared"]:
        legacy = "AUTHORIZED"
    else:
        legacy = result["status"]
    return {**result, "status": legacy}


def media_workflow_status(classification: dict, *, file_present: bool, file_verified: bool,
                          acquisition_permitted: bool) -> str:
    """Return the production gate state independently from legal categorization."""
    if classification.get("category") == "UNUSABLE":
        return "UNUSABLE"
    if not classification.get("operationally_cleared"):
        return "WAITING_FOR_RIGHTS_REVIEW"
    if not acquisition_permitted:
        return "WAITING_FOR_RIGHTS_REVIEW"
    if not file_present or not file_verified:
        return "WAITING_FOR_FILE"
    return "READY_FOR_EDIT"


def asset_id(file_path: str | Path, source_url: str) -> str:
    path = Path(file_path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    key = hashlib.sha256((source_url + "\0" + digest).encode("utf-8")).hexdigest()[:16]
    return f"yz-{key}"


def register_authorized_asset(source: dict, file_path: str | Path, *, checked_at: str, attribution: str = "") -> dict:
    """Register an existing cleared asset; never downloads or imports media."""
    classification = classify_rights(source)
    if not classification["operationally_cleared"]:
        raise ValueError(f"Asset is not cleared for this production: {classification['category']} — {classification['reason']}")
    path = Path(file_path).resolve()
    library = LIBRARY_ROOT.resolve()
    if library not in path.parents or not path.is_file():
        raise ValueError(f"Asset must be an existing file within {library}")
    evidence = source.get("rights_evidence") or {}
    entry = {
        "asset_id": asset_id(path, source["source_url"]),
        "path": str(path.relative_to(ROOT)), "game": source.get("game", ""),
        "characters": source.get("characters", []), "scene_tags": source.get("scene_tags", []),
        "tags": source.get("tags", []), "source_url": source["source_url"],
        "owner": source.get("owner") or source.get("creator"),
        "rights_category": classification["category"],
        "license": evidence.get("license_name") or evidence.get("basis") or "scoped legal assessment",
        "license_url": evidence.get("license_url"), "checked_at": checked_at,
        "scope": evidence.get("scope") or (source.get("copyright_exception") or {}).get("legal_assessment", {}).get("scope", ""),
        "expires_at": evidence.get("expires_at"),
        "permitted_platforms": evidence.get("permitted_platforms") or classification.get("target_platforms", []),
        "commercial_use": evidence.get("commercial_use", classification.get("commercial_use", False)),
        "editing_allowed": evidence.get("editing_allowed", classification["category"] == "COPYRIGHT_EXCEPTION_CANDIDATE"),
        "underlying_rights_cleared": evidence.get("underlying_rights_cleared", classification["category"] == "COPYRIGHT_EXCEPTION_CANDIDATE"),
        "legal_assessment": (source.get("copyright_exception") or {}).get("legal_assessment"),
        "attribution": attribution, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "status": "CLEARED_FOR_RECORDED_SCOPE",
    }
    LIBRARY_ROOT.mkdir(parents=True, exist_ok=True)
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8")) if INDEX_PATH.exists() else {"schema_version": 2, "assets": []}
    index["schema_version"] = 2
    index["assets"] = [item for item in index.get("assets", []) if item.get("asset_id") != entry["asset_id"]]
    index["assets"].append(entry)
    INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return entry

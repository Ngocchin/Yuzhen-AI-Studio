"""Rights-first media source classification and local authorized asset registry."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
LIBRARY_ROOT = ROOT / "assets/library"
INDEX_PATH = LIBRARY_ROOT / "index.json"
STATUSES = {"AUTHORIZED", "REVIEW_REQUIRED", "UNUSABLE"}
PLATFORMS = {"youtube", "tiktok", "douyin", "official", "creative_commons", "creator", "other"}


def _http_url(value: str) -> bool:
    parsed = urlparse(value or "")
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def classify_source(source: dict) -> dict:
    """Classify only from explicit rights evidence; platform identity is not evidence."""
    if not isinstance(source, dict):
        raise TypeError("source must be a dict")
    evidence = source.get("rights_evidence") or {}
    basis = str(evidence.get("basis", "")).strip()
    license_url = evidence.get("license_url")
    permitted = evidence.get("permitted_platforms") or []
    commercial = evidence.get("commercial_use") is True
    derivatives = evidence.get("editing_allowed") is True
    all_rights = evidence.get("underlying_rights_cleared") is True

    if evidence.get("prohibited") is True or evidence.get("drm_or_access_bypass_required") is True:
        status, reason = "UNUSABLE", "Use is prohibited or would require bypassing access/DRM restrictions."
    elif (
        basis in {"user_ownership", "written_permission", "license"}
        and bool(source.get("owner"))
        and bool(source.get("source_url"))
        and (basis == "user_ownership" or _http_url(license_url) or bool(evidence.get("permission_record")))
        and {"youtube", "tiktok"}.issubset(set(permitted))
        and commercial and derivatives and all_rights
        and bool(evidence.get("scope"))
    ):
        status, reason = "AUTHORIZED", "Explicit evidence covers editing, underlying rights, commercial use, and both target platforms."
    elif evidence.get("review_basis") and source.get("source_url"):
        status, reason = "REVIEW_REQUIRED", str(evidence["review_basis"])
    else:
        status, reason = "UNUSABLE", "No verifiable rights basis covers the intended use; public availability and attribution are insufficient."

    return {"status": status, "reason": reason}


def asset_id(file_path: str | Path, source_url: str) -> str:
    path = Path(file_path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    key = hashlib.sha256((source_url + "\0" + digest).encode("utf-8")).hexdigest()[:16]
    return f"yz-{key}"


def register_authorized_asset(source: dict, file_path: str | Path, *, checked_at: str, attribution: str = "") -> dict:
    """Register existing authorized bytes; never downloads or imports platform media."""
    classification = classify_source(source)
    if classification["status"] != "AUTHORIZED":
        raise ValueError(f"Only AUTHORIZED sources can be registered: {classification['status']} — {classification['reason']}")
    path = Path(file_path).resolve()
    library = LIBRARY_ROOT.resolve()
    if library not in path.parents or not path.is_file():
        raise ValueError(f"Asset must be an existing file within {library}")
    entry = {
        "asset_id": asset_id(path, source["source_url"]),
        "path": str(path.relative_to(ROOT)),
        "source_url": source["source_url"],
        "owner": source["owner"],
        "license": source["rights_evidence"].get("license_name") or source["rights_evidence"]["basis"],
        "license_url": source["rights_evidence"].get("license_url"),
        "checked_at": checked_at,
        "scope": source["rights_evidence"]["scope"],
        "permitted_platforms": source["rights_evidence"]["permitted_platforms"],
        "commercial_use": source["rights_evidence"]["commercial_use"],
        "editing_allowed": source["rights_evidence"]["editing_allowed"],
        "attribution": attribution,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "status": "AUTHORIZED",
    }
    LIBRARY_ROOT.mkdir(parents=True, exist_ok=True)
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8")) if INDEX_PATH.exists() else {"schema_version": 1, "assets": []}
    index["assets"] = [item for item in index["assets"] if item.get("asset_id") != entry["asset_id"]]
    index["assets"].append(entry)
    INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return entry

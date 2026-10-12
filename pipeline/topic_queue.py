"""Local backlog and URL deduplication for high-story, low-feasibility topics."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "outputs/topic-backlog.json"
DEFAULT_SOURCE_LEDGER = ROOT / "outputs/media-source-ledger.json"
TRACKING_KEYS = {"fbclid", "gclid", "si", "feature", "utm_source", "utm_medium", "utm_campaign"}


def source_key(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key.casefold() not in TRACKING_KEYS]
    normalized = urlunsplit((parts.scheme.casefold(), parts.netloc.casefold(), parts.path.rstrip("/"), urlencode(query), ""))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def filter_previously_rejected(sources: list[dict], ledger: dict) -> list[dict]:
    rejected = set(ledger.get("rejected_source_keys", []))
    return [item for item in sources if source_key(item.get("url") or item.get("source_url", "")) not in rejected]


def record_source_decision(url: str, status: str, reason: str, path: Path = DEFAULT_SOURCE_LEDGER) -> dict:
    """Cache a rights decision to avoid repeating dead-end searches until evidence changes."""
    if status not in {"AUTHORIZED", "REVIEW_REQUIRED", "UNUSABLE"}:
        raise ValueError("status must be AUTHORIZED, REVIEW_REQUIRED, or UNUSABLE")
    path = Path(path)
    ledger = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"schema_version": 1, "items": [], "rejected_source_keys": []}
    key = source_key(url)
    ledger["items"] = [item for item in ledger.get("items", []) if item.get("source_key") != key]
    entry = {"source_key": key, "url": url, "status": status, "reason": reason}
    ledger["items"].append(entry)
    if status != "AUTHORIZED":
        ledger["rejected_source_keys"] = sorted(set(ledger.get("rejected_source_keys", [])) | {key})
    else:
        ledger["rejected_source_keys"] = [old for old in ledger.get("rejected_source_keys", []) if old != key]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return entry


def record_waiting_topic(topic: dict, path: Path = DEFAULT_QUEUE) -> dict:
    path = Path(path)
    queue = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"schema_version": 1, "items": []}
    identity = hashlib.sha256(str(topic["title"]).strip().casefold().encode("utf-8")).hexdigest()
    item = {**topic, "topic_id": f"topic-{identity[:12]}", "status": "WAITING_FOR_MEDIA", "rejected_source_keys": sorted({source_key(url) for url in topic.get("rejected_source_urls", [])})}
    queue["items"] = [old for old in queue.get("items", []) if old.get("topic_id") != item["topic_id"]]
    queue["items"].append(item)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return item

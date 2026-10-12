"""Persistent story-first topic filtering and scoring for Yuzhen."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/content-strategy.json"
SCORE_FIELDS = (
    "story_appeal",
    "conflict_mystery_climax",
    "curiosity_hook",
    "emotion_debate",
    "gaming_community_fit",
    "rights_cleared_media_feasibility",
)
ADMIN_TERMS = (
    "xe bus", "xe đưa đón", "đăng ký nhận vé", "lịch nhận vé", "nhận vé",
    "hướng dẫn nhận quà", "bảo trì", "khuyến mãi", "nhập code",
    "lịch sự kiện", "địa điểm tổ chức", "cách đăng ký",
)
FACT_TYPES = {"CANON", "REAL_EVENT", "REAL_MATCH", "REAL_GAMEPLAY"}


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def topic_decision(topic: dict[str, Any]) -> dict[str, Any]:
    """Apply admin-topic hard filters and evidence gate before ranking."""
    title = str(topic.get("title", ""))
    text = f"{title} {topic.get('description', '')}".casefold()
    category = str(topic.get("category", "")).upper()
    narrative = bool(topic.get("story_angle"))
    rejected = bool(topic.get("admin_only"))
    reasons: list[str] = []
    if rejected:
        reasons.append("admin_only")
    matched = [term for term in ADMIN_TERMS if term in text]
    if matched and not (category == "EVENT_HISTORY" and narrative):
        rejected = True
        reasons.append("administrative_or_transactional_topic")

    claim_type = str(topic.get("claim_type", "REAL_EVENT")).upper()
    sources = topic.get("sources") or []
    has_source = any(isinstance(s, str) and s.startswith("https://") for s in sources)
    if claim_type in FACT_TYPES and not has_source:
        reasons.append("real_story_missing_source")
    elif claim_type not in FACT_TYPES and claim_type not in {"FAN_THEORY", "FICTION"}:
        reasons.append("claim_type_must_be_canon_real_event_fan_theory_or_fiction")

    eligible = not rejected and not any(
        r in reasons for r in ("real_story_missing_source", "claim_type_must_be_canon_real_event_fan_theory_or_fiction")
    )
    return {"eligible": eligible, "reasons": reasons, "matched_admin_terms": matched}


def storytelling_score(scores: dict[str, int]) -> int:
    """Validate 0–max dimension values and return weighted score out of 100."""
    config = load_config()["storytelling_score"]["weights"]
    if set(scores) != set(config):
        raise ValueError(f"scores must contain exactly: {', '.join(config)}")
    total = 0
    for field in config:
        value = scores[field]
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= config[field]:
            raise ValueError(f"{field} must be an integer in [0, {config[field]}]")
        total += value
    return total


def rank_score(story_score: int, viral_potential_score: int) -> float:
    if not 0 <= story_score <= 100 or not 0 <= viral_potential_score <= 100:
        raise ValueError("scores must be in [0, 100]")
    ranking = load_config()["ranking"]
    return round(story_score * ranking["storytelling_score_weight"] + viral_potential_score * ranking["viral_potential_score_weight"], 2)


def classify_claim(text: str, requested_type: str, has_sources: bool) -> str:
    """Prevent unsupported real-world/canon claims from being narrated as fact."""
    kind = requested_type.upper()
    if kind in FACT_TYPES and not has_sources:
        raise ValueError("real or canon claims require at least one evidence source")
    if kind not in FACT_TYPES | {"FAN_THEORY", "FICTION"}:
        raise ValueError("claim must be explicitly classified as CANON, REAL_EVENT, REAL_MATCH, REAL_GAMEPLAY, FAN_THEORY, or FICTION")
    del text
    return kind

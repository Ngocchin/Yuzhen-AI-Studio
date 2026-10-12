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
    "narrative_originality_and_clarity",
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


def rank_score(story_score: int, viral_potential_score: int, media_feasibility_score: int) -> float:
    """Production priority; Hot/Viral Potential remains a separate input."""
    return production_priority_score(story_score, viral_potential_score, media_feasibility_score)


def production_priority_score(story_score: int, viral_potential_score: int, media_feasibility_score: int) -> float:
    """Rank production readiness separately; this score is not a popularity signal."""
    values = (story_score, viral_potential_score, media_feasibility_score)
    if any(isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 100 for v in values):
        raise ValueError("story, viral, and media feasibility scores must be integers in [0, 100]")
    weights = load_config()["ranking"]
    total = sum((
        weights["storytelling_score_weight"],
        weights["viral_potential_score_weight"],
        weights["media_feasibility_score_weight"],
    ))
    if abs(total - 1.0) > 1e-9:
        raise ValueError("production priority weights must sum to 1")
    return round(
        story_score * weights["storytelling_score_weight"]
        + viral_potential_score * weights["viral_potential_score_weight"]
        + media_feasibility_score * weights["media_feasibility_score_weight"], 2
    )


def choose_production_topic(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Prefer Story-qualified candidates whose visual plan clears the readiness threshold."""
    policy = load_config()
    story_floor = policy["storytelling_score"]["minimum"]
    media_floor = policy["media_feasibility"]["production_minimum"]
    qualified = [item for item in candidates if item.get("qualified_for_shortlist") and item.get("storytelling_score", -1) >= story_floor]
    ready = [item for item in qualified if item.get("media_feasibility_score", 0) >= media_floor and item.get("media_feasibility", {}).get("production_ready_estimate", False)]
    waiting = [item for item in qualified if item not in ready]
    order = lambda item: (item.get("production_priority_score", 0), item.get("storytelling_score", 0), item.get("media_feasibility_score", 0))
    ready.sort(key=order, reverse=True)
    waiting.sort(key=order, reverse=True)
    return {"selected": ready[0] if ready else None, "ready": ready, "waiting": waiting, "ranked": ready + waiting, "production_blocked": not bool(ready)}


def classify_claim(text: str, requested_type: str, has_sources: bool) -> str:
    """Prevent unsupported real-world/canon claims from being narrated as fact."""
    kind = requested_type.upper()
    if kind in FACT_TYPES and not has_sources:
        raise ValueError("real or canon claims require at least one evidence source")
    if kind not in FACT_TYPES | {"FAN_THEORY", "FICTION"}:
        raise ValueError("claim must be explicitly classified as CANON, REAL_EVENT, REAL_MATCH, REAL_GAMEPLAY, FAN_THEORY, or FICTION")
    del text
    return kind

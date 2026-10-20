"""Estimate production feasibility without treating it as rights clearance or virality."""
from __future__ import annotations

from typing import Any

from pipeline.story_strategy import load_config


def score_media_feasibility(scenes: list[dict[str, Any]]) -> dict[str, Any]:
    if not scenes:
        raise ValueError("at least one illustrative scene is required")
    values = load_config()["media_feasibility"]["scene_values"]
    scored = []
    for index, scene in enumerate(scenes, 1):
        kind = scene.get("visual_plan")
        if kind == "authorized_asset" and scene.get("rights_status") == "AUTHORIZED" and scene.get("asset_id"):
            points, reason = values["authorized_asset"], "Existing asset has an authorization record."
        elif (
            kind == "fact_grounded_original_graphic"
            and scene.get("uses_third_party_art") is False
            and scene.get("clearly_labeled_as_illustration") is True
            and any(str(url).startswith("https://") for url in scene.get("fact_sources", []))
        ):
            points, reason = values["fact_grounded_original_graphic"], "Original graphic can be made from cited facts without game/broadcast artwork."
        elif (
            kind == "clearly_labeled_fiction_graphic"
            and scene.get("claim_type") == "FICTION"
            and scene.get("uses_third_party_art") is False
            and scene.get("clearly_labeled_as_illustration") is True
        ):
            points, reason = values["fact_grounded_original_graphic"], "Original visual can illustrate a disclosed fictional scenario without game/broadcast artwork."
        elif kind == "review_required_asset" or scene.get("rights_status") == "REVIEW_REQUIRED":
            points, reason = values["review_required_asset"], "Asset needs a rights decision; it cannot enter a release render yet."
        else:
            points, reason = values["missing"], "No authorized asset or sufficiently sourced original visual plan."
        scored.append({"scene": scene.get("id", index), "score": points, "reason": reason})
    score = round(sum(item["score"] for item in scored) / len(scored))
    threshold = load_config()["media_feasibility"]["production_minimum"]
    return {
        "score": score,
        "production_ready_estimate": score >= threshold,
        "minimum": threshold,
        "scenes": scored,
        "not_a_rights_or_virality_finding": True,
    }

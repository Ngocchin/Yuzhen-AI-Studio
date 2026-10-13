import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline.media_feasibility import score_media_feasibility
from pipeline.story_strategy import production_priority_score
from pipeline.topic_queue import filter_previously_rejected, record_source_decision, record_waiting_topic, source_key


class MediaFeasibilityTests(unittest.TestCase):
    def test_factual_original_graphic_scores_production_feasibility_without_claiming_rights(self):
        result = score_media_feasibility([{
            "id": "game-seven", "visual_plan": "fact_grounded_original_graphic",
            "fact_sources": ["https://official.example/recap"], "uses_third_party_art": False,
            "clearly_labeled_as_illustration": True,
        }])
        self.assertEqual(result["score"], 85)
        self.assertTrue(result["production_ready_estimate"])
        self.assertTrue(result["not_a_rights_or_virality_finding"])

    def test_public_video_does_not_unlock_feasibility(self):
        result = score_media_feasibility([{"visual_plan": "review_required_asset", "rights_status": "REVIEW_REQUIRED"}])
        self.assertEqual(result["score"], 25)
        self.assertFalse(result["production_ready_estimate"])

    def test_graphics_without_source_or_disclosure_do_not_score_as_feasible(self):
        result = score_media_feasibility([{"visual_plan": "fact_grounded_original_graphic", "fact_sources": [], "uses_third_party_art": False}])
        self.assertEqual(result["score"], 0)

    def test_storytelling_viral_and_feasibility_are_combined_only_for_production_priority(self):
        self.assertGreater(production_priority_score(82, 70, 90), production_priority_score(90, 95, 20))

    def test_waiting_topics_are_deduplicated_and_known_rejected_urls_filtered(self):
        url = "https://youtube.com/watch?v=abc&utm_source=search"
        self.assertEqual(source_key(url), source_key("https://youtube.com/watch?v=abc"))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "topic-backlog.json"
            first = record_waiting_topic({"title": "AWC 2019", "rejected_source_urls": [url]}, path)
            second = record_waiting_topic({"title": "AWC 2019", "rejected_source_urls": [url]}, path)
            self.assertEqual(first["topic_id"], second["topic_id"])
            queue = json.loads(path.read_text())
            self.assertEqual(len(queue["items"]), 1)
            remaining = filter_previously_rejected([{"url": "https://youtube.com/watch?v=abc"}, {"url": "https://example.com/new"}], {"rejected_source_keys": first["rejected_source_keys"]})
            self.assertEqual([row["url"] for row in remaining], ["https://example.com/new"])

    def test_source_decisions_suppress_dead_urls_until_new_permission(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source-ledger.json"
            url = "https://creator.example/clip"
            record_source_decision(url, "REVIEW_REQUIRED", "Exception candidate awaiting assessment", path,
                                   category="COPYRIGHT_EXCEPTION_CANDIDATE",
                                   supporting_factors=["specific commentary"],
                                   opposing_factors=["rights unresolved"])
            ledger = json.loads(path.read_text())
            self.assertEqual(ledger["schema_version"], 2)
            self.assertEqual(ledger["items"][0]["rights_category"], "COPYRIGHT_EXCEPTION_CANDIDATE")
            self.assertEqual(ledger["items"][0]["opposing_factors"], ["rights unresolved"])
            self.assertEqual(filter_previously_rejected([{"url": url}], ledger), [])
            record_source_decision(url, "AUTHORIZED", "New written rights receipt", path)
            ledger = json.loads(path.read_text())
            self.assertEqual(filter_previously_rejected([{"url": url}], ledger), [{"url": url}])


if __name__ == "__main__":
    unittest.main()

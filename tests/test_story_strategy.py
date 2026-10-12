import unittest

from pipeline.story_strategy import choose_production_topic, classify_claim, load_config, rank_score, storytelling_score, topic_decision


class StoryStrategyTests(unittest.TestCase):
    def test_free_event_bus_is_rejected(self):
        result = topic_decision({"title": "Xe bus cộng đồng miễn phí tới 10Fest", "admin_only": True, "category": "EVENT_HISTORY", "claim_type": "REAL_EVENT", "sources": ["https://example.org"]})
        self.assertFalse(result["eligible"])
        self.assertIn("admin_only", result["reasons"])

    def test_ticket_schedule_only_is_rejected(self):
        result = topic_decision({"title": "Lịch đăng ký nhận vé sự kiện", "category": "EVENT_HISTORY", "claim_type": "REAL_EVENT", "sources": ["https://example.org"]})
        self.assertFalse(result["eligible"])

    def test_sourced_character_lore_is_eligible(self):
        result = topic_decision({"title": "Cuộc chiến ba sát thủ và dị tượng", "category": "CHARACTER", "claim_type": "CANON", "sources": ["https://lienquan.garena.vn/story"]})
        self.assertTrue(result["eligible"])

    def test_sourced_historical_match_is_eligible(self):
        result = topic_decision({"title": "Chung kết AWC 2019 kéo tới ván bảy", "category": "EVENT_HISTORY", "story_angle": "series final", "claim_type": "REAL_MATCH", "sources": ["https://official.example/match"]})
        self.assertTrue(result["eligible"])

    def test_story_event_is_eligible_but_administrative_event_is_not(self):
        result = topic_decision({"title": "Trận chung kết thay đổi lịch sử đội tuyển", "category": "EVENT_HISTORY", "story_angle": "underdog comeback", "claim_type": "REAL_EVENT", "sources": ["https://official.example/event"]})
        self.assertTrue(result["eligible"])

    def test_unsourced_real_claim_is_blocked(self):
        result = topic_decision({"title": "Bí mật canon của tướng", "category": "MYSTERY", "claim_type": "CANON", "sources": []})
        self.assertFalse(result["eligible"])
        with self.assertRaises(ValueError):
            classify_claim("unsupported lore", "CANON", has_sources=False)

    def test_scoring_threshold_and_rank_weights(self):
        self.assertEqual(storytelling_score({"story_appeal": 25, "conflict_mystery_climax": 20, "curiosity_hook": 20, "emotion_debate": 15, "gaming_community_fit": 10, "narrative_originality_and_clarity": 10}), 100)
        self.assertEqual(rank_score(80, 60, 100), 82.0)
        self.assertEqual(rank_score(100, 100, 0), 70.0)
        self.assertEqual(load_config()["storytelling_score"]["minimum"], 75)
        self.assertNotIn("media_feasibility", load_config()["storytelling_score"]["weights"])

    def test_media_feasibility_is_not_in_storytelling_or_viral_weights(self):
        ranking = load_config()["ranking"]
        self.assertAlmostEqual(sum(ranking[key] for key in ("storytelling_score_weight", "viral_potential_score_weight", "media_feasibility_score_weight")), 1.0)
        self.assertFalse(load_config()["ranking"]["viral_score_is_prediction"])

    def test_production_selector_prefers_feasible_topic_and_waitlists_blocked_story(self):
        feasible = {"title": "Original diagram story", "qualified_for_shortlist": True, "storytelling_score": 80, "viral_potential_score": 65, "media_feasibility_score": 85, "production_priority_score": 78.5, "media_feasibility": {"production_ready_estimate": True}}
        blocked = {"title": "Needs broadcast clip", "qualified_for_shortlist": True, "storytelling_score": 96, "viral_potential_score": 98, "media_feasibility_score": 25, "production_priority_score": 75.3, "media_feasibility": {"production_ready_estimate": False}}
        selected = choose_production_topic([blocked, feasible])
        self.assertEqual(selected["selected"]["title"], "Original diagram story")
        self.assertEqual([item["title"] for item in selected["waiting"]], ["Needs broadcast clip"])

    def test_selector_blocks_when_every_qualified_story_is_unrenderable(self):
        result = choose_production_topic([{"title": "no assets", "qualified_for_shortlist": True, "storytelling_score": 95, "media_feasibility_score": 10, "media_feasibility": {"production_ready_estimate": False}}])
        self.assertTrue(result["production_blocked"])
        self.assertIsNone(result["selected"])

    def test_category_preferences_break_ties_after_feasibility_priority(self):
        common = {"qualified_for_shortlist": True, "storytelling_score": 80, "viral_potential_score": 80, "media_feasibility_score": 85, "production_priority_score": 81.5, "media_feasibility": {"production_ready_estimate": True}}
        result = choose_production_topic([{**common, "title": "Esports", "category": "ESPORTS"}, {**common, "title": "Character", "category": "CHARACTER"}])
        self.assertEqual(result["selected"]["title"], "Character")

    def test_min_quan_is_required_voice(self):
        config = load_config()["voice"]
        self.assertEqual(config["engine"], "VieNeu-TTS")
        self.assertEqual(config["version"], "3.7.1")
        self.assertEqual(config["preset"], "Minh Quân")
        self.assertTrue(config["required"])
        self.assertTrue(config["block_if_unavailable"])


if __name__ == "__main__":
    unittest.main()

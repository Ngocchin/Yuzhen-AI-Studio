import unittest

from pipeline.story_strategy import classify_claim, load_config, rank_score, storytelling_score, topic_decision


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
        self.assertEqual(storytelling_score({"story_appeal": 25, "conflict_mystery_climax": 20, "curiosity_hook": 20, "emotion_debate": 15, "gaming_community_fit": 10, "rights_cleared_media_feasibility": 10}), 100)
        self.assertEqual(rank_score(80, 60), 74.0)
        self.assertEqual(load_config()["storytelling_score"]["minimum"], 75)

    def test_min_quan_is_required_voice(self):
        config = load_config()["voice"]
        self.assertEqual(config["engine"], "VieNeu-TTS")
        self.assertEqual(config["version"], "3.7.1")
        self.assertEqual(config["preset"], "Minh Quân")
        self.assertTrue(config["required"])
        self.assertTrue(config["block_if_unavailable"])


if __name__ == "__main__":
    unittest.main()

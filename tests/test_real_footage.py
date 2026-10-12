import unittest

from pipeline.real_footage import normalize_game, preflight_real_footage


class RealFootageFirstTests(unittest.TestCase):
    def setUp(self):
        self.scenes = [{"id": "01", "narration": "Volkath trở lại"}]

    def candidate(self, **updates):
        row = {
            "candidate_id": "candidate-1", "title": "Volkath highlight", "platform": "youtube",
            "source_url": "https://youtube.com/watch?v=one", "owner": "Creator",
            "game": "Arena of Valor", "game_identity_verified": True,
            "duration_seconds": 60, "rights_evidence": {"review_basis": "No reuse grant found"},
            "scene_matches": [{"scene_id": "01", "in_seconds": 3.0, "out_seconds": 8.0,
                               "confidence": "MEDIUM", "editorial_match": "Character appears"}],
        }
        row.update(updates)
        return row

    def test_search_match_without_rights_stays_review_required_and_does_not_render(self):
        result = preflight_real_footage(self.scenes, [self.candidate()], mode="SAFE")
        self.assertEqual(result["status"], "NEEDS_FOOTAGE_RIGHTS")
        self.assertFalse(result["may_render"])
        self.assertFalse(result["generated_graphics_fallback"])
        self.assertEqual(result["scene_matches"][0]["rights_status"], "REVIEW_REQUIRED")

    def test_internal_review_needs_separate_retrieval_and_use_evidence(self):
        candidate = self.candidate(internal_review_evidence={
            "retrieval_permitted": True, "internal_use_permitted": True,
            "evidence_record": "written-approval-42",
        })
        result = preflight_real_footage(self.scenes, [candidate], mode="INTERNAL_REVIEW")
        self.assertFalse(result["may_render"], "must also have verified media in the private library")
        self.assertEqual(result["status"], "NEEDS_FOOTAGE_RIGHTS")

    def test_honor_of_kings_is_not_mapped_to_arena_of_valor(self):
        self.assertNotEqual(normalize_game("Honor of Kings"), normalize_game("Arena of Valor"))
        candidate = self.candidate(game="Honor of Kings")
        result = preflight_real_footage(self.scenes, [candidate], expected_game="Arena of Valor")
        self.assertEqual(len(result["scene_matches"]), 1)
        self.assertEqual(result["scene_matches"][0]["confidence"], "NONE")
        self.assertFalse(result["may_render"])

    def test_unverified_game_identity_cannot_enter_edit(self):
        result = preflight_real_footage(self.scenes, [self.candidate(game_identity_verified=False)], mode="SAFE")
        self.assertFalse(result["may_render"])
        self.assertIn("01", result["missing_scene_ids"])

    def test_invalid_modes_fail_closed(self):
        with self.assertRaises(ValueError):
            preflight_real_footage(self.scenes, [], mode="PUBLIC")


if __name__ == "__main__":
    unittest.main()

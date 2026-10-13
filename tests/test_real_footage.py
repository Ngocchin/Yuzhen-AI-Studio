import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline import real_footage
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

    def test_search_match_without_a_recorded_use_basis_is_unusable_and_does_not_render(self):
        result = preflight_real_footage(self.scenes, [self.candidate()], mode="SAFE")
        self.assertEqual(result["status"], "NEEDS_FOOTAGE_RIGHTS")
        self.assertFalse(result["may_render"])
        self.assertFalse(result["generated_graphics_fallback"])
        self.assertEqual(result["scene_matches"][0]["rights_status"], "UNUSABLE")
        self.assertEqual(result["scene_matches"][0]["rights_category"], "UNUSABLE")

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

    def test_platform_remix_never_enters_local_ffmpeg_edit(self):
        candidate = self.candidate(
            local_path="assets/media-library/clip.mp4",
            rights_evidence={"platform_remix": {"enabled_by_owner": True, "feature": "stitch", "platform": "tiktok", "native_feature_only": True, "verification_record": "settings-visible"}},
            internal_review_evidence={"retrieval_permitted": True, "internal_use_permitted": True, "evidence_record": "review-copy"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            library = Path(tmp) / "assets/media-library"
            library.mkdir(parents=True)
            (library / "clip.mp4").write_bytes(b"fixture")
            with patch.object(real_footage, "LIBRARY_ROOT", library), patch.object(real_footage, "_probe", return_value={"verified": True}):
                result = preflight_real_footage(self.scenes, [candidate], mode="INTERNAL_REVIEW", production_dir=tmp)
        self.assertFalse(result["may_render"])
        self.assertEqual(result["scene_matches"][0]["rights_category"], "PLATFORM_REMIX")

    def test_scoped_exception_assessment_can_clear_only_its_mapped_scene(self):
        candidate = self.candidate(
            duration_seconds=1,
            local_path="assets/media-library/clip.mp4",
            scene_matches=[{"scene_id": "01", "in_seconds": 0.2, "out_seconds": 0.9, "confidence": "HIGH", "editorial_match": "The mechanic is analyzed"}],
            rights_evidence={},
            copyright_exception={
                "identified_rights_holders": ["Broadcaster", "Game publisher"],
                "editorial_purpose": "criticism and analysis",
                "commentary_map": [{"scene_id": "01", "commentary_text": "Compare the claim with the observed mechanic.", "analysis_function": "test the story's gameplay interpretation"}],
                "source_acquisition_basis": "Publisher supplied review copy",
                "source_access_legitimate": True,
                "jurisdiction": "VN",
                "amount_rationale": "The reviewer scoped the exact beat needed for the analysis.",
                "market_effect_analysis": "Reviewer considered substitution and licensing market.",
                "supporting_factors": ["Direct criticism"],
                "opposing_factors": ["Commercial use"],
                "legal_assessment": {"outcome": "approved_for_intended_use", "assessment_record": "assessment-1", "reviewer": "Reviewer", "jurisdiction": "VN", "rights_holders_reviewed": True, "platforms": ["youtube", "tiktok"], "commercial_use": True, "scope": "Scene 01 only"},
            },
        )
        with tempfile.TemporaryDirectory() as tmp:
            library = Path(tmp) / "assets/media-library"
            library.mkdir(parents=True)
            (library / "clip.mp4").write_bytes(b"fixture")
            with patch.object(real_footage, "LIBRARY_ROOT", library), patch.object(real_footage, "_probe", return_value={"verified": True}):
                result = preflight_real_footage(self.scenes, [candidate], mode="SAFE", production_dir=tmp)
        self.assertTrue(result["may_render"])
        self.assertEqual(result["scene_matches"][0]["rights_category"], "COPYRIGHT_EXCEPTION_CANDIDATE")
        self.assertEqual(result["status"], "READY_FOR_PUBLICATION_REVIEW")


if __name__ == "__main__":
    unittest.main()

import unittest

from pipeline.media_sources import classify_rights, classify_source


class MediaSourceRightsTests(unittest.TestCase):
    def test_explicit_scope_and_rights_are_required_for_authorized(self):
        candidate = {
            "title": "Original game clip",
            "source_url": "https://creator.example/video/1",
            "owner": "Creator",
            "platform": "youtube",
            "rights_evidence": {
                "basis": "written_permission",
                "permission_record": "permission-2026-01",
                "permitted_platforms": ["youtube", "tiktok"],
                "commercial_use": True,
                "editing_allowed": True,
                "underlying_rights_cleared": True,
                "scope": "Edited vertical commentary clips on the named channels",
            },
        }
        self.assertEqual(classify_source(candidate)["status"], "AUTHORIZED")
        self.assertEqual(classify_rights(candidate)["category"], "LICENSED_OR_PERMITTED")

    def test_public_or_credit_only_video_requires_review(self):
        candidate = {"source_url": "https://youtube.com/watch?v=public", "owner": "Creator", "platform": "youtube", "rights_evidence": {}}
        self.assertEqual(classify_rights(candidate)["category"], "UNUSABLE")

    def test_official_account_does_not_imply_reuse_rights(self):
        candidate = {"source_url": "https://youtube.com/watch?v=official", "owner": "Game Publisher", "platform": "youtube", "rights_evidence": {"review_basis": "Official upload; no reuse grant found."}}
        self.assertEqual(classify_rights(candidate)["category"], "UNUSABLE")

    def test_incomplete_platform_or_underlying_rights_never_authorizes(self):
        candidate = {
            "source_url": "https://creator.example/video/2",
            "owner": "Creator",
            "rights_evidence": {
                "basis": "license", "license_url": "https://creator.example/license",
                "permitted_platforms": ["youtube"], "commercial_use": True,
                "editing_allowed": True, "underlying_rights_cleared": False,
                "scope": "Edited video",
            },
        }
        self.assertEqual(classify_rights(candidate)["category"], "UNUSABLE")

    def test_explicit_prohibition_or_bypass_is_unusable(self):
        candidate = {"source_url": "https://example.org/a", "owner": "Unknown", "rights_evidence": {"review_basis": "Maybe fair use", "drm_or_access_bypass_required": True}}
        self.assertEqual(classify_source(candidate)["status"], "UNUSABLE")

    def test_expired_permission_is_unusable(self):
        candidate = {
            "source_url": "https://creator.example/video/3", "owner": "Creator",
            "rights_evidence": {
                "basis": "license", "license_url": "https://creator.example/license",
                "expires_at": "2000-01-01T00:00:00Z", "permitted_platforms": ["youtube", "tiktok"],
                "commercial_use": True, "editing_allowed": True,
                "underlying_rights_cleared": True, "scope": "Edited vertical commentary",
            },
        }
        self.assertEqual(classify_source(candidate)["status"], "UNUSABLE")

    def test_platform_remix_is_native_feature_only_and_not_cross_platform_clearance(self):
        candidate = {
            "title": "Creator clip", "source_url": "https://tiktok.com/@creator/video/4", "owner": "Creator",
            "rights_evidence": {"platform_remix": {"enabled_by_owner": True, "feature": "stitch", "platform": "tiktok", "native_feature_only": True, "verification_record": "settings-visible-2026-10-13"}},
        }
        result = classify_rights(candidate)
        self.assertEqual(result["category"], "PLATFORM_REMIX")
        self.assertFalse(result["operationally_cleared"])
        self.assertEqual(result["permitted_platform"], "tiktok")

    def test_exception_case_without_assessment_stays_candidate_and_never_uses_a_seconds_threshold(self):
        candidate = {
            "title": "Match highlight", "source_url": "https://youtube.com/watch?v=analysis", "owner": "Broadcaster",
            "duration_seconds": 1.0,
            "copyright_exception": {
                "identified_rights_holders": ["Broadcaster/source uploader (not verified)", "Garena/Tencent (underlying game rights to verify)"],
                "editorial_purpose": "criticism and analysis",
                "commentary_map": [{"scene_id": "4", "commentary_text": "Compare the lore claim to this mechanic.", "analysis_function": "test a factual claim"}],
                "source_acquisition_basis": "Publicly accessible page; no downloading performed",
                "amount_rationale": "Use only the specific beat needed to compare the historical mechanic, after source inspection.",
                "market_effect_analysis": "Unresolved; the game publisher or broadcaster may control commercial exploitation.",
                "jurisdiction": "VN",
                "supporting_factors": ["Specific analysis directly addresses the excerpt"],
                "opposing_factors": ["Commercial use is planned", "Underlying broadcast rights are unresolved"],
            },
        }
        result = classify_rights(candidate)
        self.assertEqual(result["category"], "COPYRIGHT_EXCEPTION_CANDIDATE")
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertFalse(result["operationally_cleared"])
        self.assertTrue(result["duration_is_not_a_rule"])

    def test_exception_requires_scoped_human_assessment_for_operational_clearance(self):
        candidate = {
            "title": "Match highlight", "source_url": "https://youtube.com/watch?v=analysis", "owner": "Broadcaster",
            "copyright_exception": {
                "identified_rights_holders": ["Broadcaster/source uploader", "Garena/Tencent (underlying game rights assessed)"],
                "editorial_purpose": "criticism and analysis",
                "commentary_map": [{"scene_id": "4", "commentary_text": "Compare the lore claim to this mechanic.", "analysis_function": "test a factual claim"}],
                "source_acquisition_basis": "Source owner supplied review copy",
                "source_access_legitimate": True,
                "amount_rationale": "Use only the specific beat needed to compare the historical mechanic.",
                "market_effect_analysis": "The scoped reviewer considered substitution and the owner market.",
                "jurisdiction": "VN",
                "supporting_factors": ["Direct analysis"], "opposing_factors": ["Commercial intent"],
                "legal_assessment": {
                    "outcome": "approved_for_intended_use", "assessment_record": "assessment-2026-01",
                    "reviewer": "Qualified reviewer", "jurisdiction": "VN", "rights_holders_reviewed": True, "platforms": ["youtube", "tiktok"],
                    "commercial_use": True, "scope": "One clip mapped to scene 4 for this edited commentary video",
                },
            },
        }
        result = classify_rights(candidate)
        self.assertEqual(result["category"], "COPYRIGHT_EXCEPTION_CANDIDATE")
        self.assertTrue(result["operationally_cleared"])
        self.assertTrue(result["legal_assessment_recorded"])

    def test_no_rights_or_exception_basis_is_unusable_for_this_production(self):
        candidate = {"title": "Public video", "source_url": "https://youtube.com/watch?v=unknown", "owner": "Creator"}
        self.assertEqual(classify_rights(candidate)["category"], "UNUSABLE")

    def test_license_requires_attribution_when_its_terms_require_it(self):
        candidate = {
            "title": "Licensed game asset", "source_url": "https://stock.example/clip", "owner": "Stock owner",
            "rights_evidence": {
                "basis": "license", "license_url": "https://stock.example/license",
                "permitted_platforms": ["youtube", "tiktok"], "commercial_use": True,
                "editing_allowed": True, "underlying_rights_cleared": True,
                "scope": "Commercial vertical video", "attribution_required": True,
            },
        }
        self.assertEqual(classify_rights(candidate)["category"], "UNUSABLE")
        candidate["rights_evidence"]["attribution_text"] = "Stock owner / license URL"
        self.assertEqual(classify_rights(candidate)["category"], "LICENSED_OR_PERMITTED")


if __name__ == "__main__":
    unittest.main()

import unittest

from pipeline.media_sources import classify_source


class MediaSourceRightsTests(unittest.TestCase):
    def test_explicit_scope_and_rights_are_required_for_authorized(self):
        candidate = {
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

    def test_public_or_credit_only_video_is_unusable(self):
        candidate = {"source_url": "https://youtube.com/watch?v=public", "owner": "Creator", "platform": "youtube", "rights_evidence": {}}
        self.assertEqual(classify_source(candidate)["status"], "UNUSABLE")

    def test_official_account_does_not_imply_reuse_rights(self):
        candidate = {"source_url": "https://youtube.com/watch?v=official", "owner": "Game Publisher", "platform": "youtube", "rights_evidence": {"review_basis": "Official upload; no reuse grant found."}}
        self.assertEqual(classify_source(candidate)["status"], "REVIEW_REQUIRED")

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
        self.assertEqual(classify_source(candidate)["status"], "UNUSABLE")

    def test_explicit_prohibition_or_bypass_is_unusable(self):
        candidate = {"source_url": "https://example.org/a", "owner": "Unknown", "rights_evidence": {"review_basis": "Maybe fair use", "drm_or_access_bypass_required": True}}
        self.assertEqual(classify_source(candidate)["status"], "UNUSABLE")


if __name__ == "__main__":
    unittest.main()

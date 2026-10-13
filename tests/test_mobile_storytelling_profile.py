import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MobileStorytellingProfileTests(unittest.TestCase):
    def test_mobile_storytelling_profile_is_default_and_voice_locked(self):
        profile = json.loads((ROOT / "config/styles/yuzhen-mobile-storytelling.json").read_text(encoding="utf-8"))
        strategy = json.loads((ROOT / "config/content-strategy.json").read_text(encoding="utf-8"))
        self.assertEqual(strategy["production"]["video_style"], profile["id"])
        self.assertEqual(profile["voice"], {
            "engine": "VieNeu-TTS", "version": "3.7.1", "preset": "Minh Quân",
            "required": True, "allow_automatic_fallback": False
        })
        self.assertEqual(profile["media"]["unverified_media_action"], "report_exact_scene_gaps_and_prepare_an_edit_decision_list; do_not_render_or_substitute_vector_art")

    def test_reference_unknowns_are_not_fabricated(self):
        profile = json.loads((ROOT / "config/styles/yuzhen-mobile-storytelling.json").read_text(encoding="utf-8"))
        analysis = profile["reference_analysis"]
        self.assertEqual(analysis["status"], "AWAITING_USER_MP4")
        self.assertEqual(analysis["observed_facts"], [])
        self.assertEqual(analysis["timestamped_timeline"], [])


if __name__ == "__main__":
    unittest.main()

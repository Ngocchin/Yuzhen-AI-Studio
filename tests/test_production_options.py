import unittest

from pipeline.production_options import _scenes


class ProductionOptionTests(unittest.TestCase):
    def test_awc_option_b_is_chronological_disclosed_and_source_bound(self):
        scenes = _scenes()
        self.assertEqual(scenes[0]["start"], 0)
        self.assertEqual(scenes[-1]["end"], 35.22)
        self.assertEqual([scene["beat"] for scene in scenes], [
            "HOOK", "SETUP", "CONFLICT", "BREATH", "CLIMAX", "PAYOFF", "MEME_PAUSE", "ENDING", "END_CARD_HOLD"
        ])
        self.assertTrue(all(scene.get("disclosure") == "MINH HỌA · KHÔNG PHẢI GAMEPLAY" for scene in scenes))
        self.assertTrue(all("image_asset" not in scene for scene in scenes))
        self.assertEqual(round(sum(scene["end"] - scene["start"] for scene in scenes), 2), 35.22)


if __name__ == "__main__":
    unittest.main()

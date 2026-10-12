import json
import tempfile
import unittest
from pathlib import Path

from pipeline.event_storytelling import DEFAULT_STYLE, load_style, render_card, render_video


class EventStorytellingStyleTests(unittest.TestCase):
    def test_profile_locks_the_approved_vertical_brand_basics(self):
        style = load_style()
        self.assertEqual(style["id"], "yuzhen-event-storytelling")
        self.assertEqual(style["canvas"], {
            "width": 1080,
            "height": 1920,
            "fps": 30,
            "aspect_ratio": "9:16",
            "duration_min_seconds": 35,
            "duration_max_seconds": 50,
        })
        self.assertEqual(style["audio"]["voice_profile"], "Minh Quân")
        self.assertFalse(style["branding"]["creator_reference_logo_allowed"])

    def test_profile_rejects_incompatible_canvas(self):
        profile = json.loads(DEFAULT_STYLE.read_text())
        profile["canvas"]["width"] = 720
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "style.json"
            path.write_text(json.dumps(profile))
            with self.assertRaises(ValueError):
                load_style(path)

    def test_card_generation_produces_requested_vertical_png(self):
        style = load_style()
        with tempfile.TemporaryDirectory() as directory:
            path = render_card({"title": "Xe bus miễn phí?", "body": "Suất có hạn.", "kicker": "TIN ĐÁNG CHÚ Ý", "callout": "Đăng ký đến 20/10"}, 1, 5, Path(directory) / "card.png", style)
            from PIL import Image
            with Image.open(path) as image:
                self.assertEqual(image.size, (1080, 1920))
                self.assertEqual(image.mode, "RGB")

    def test_card_accepts_a_local_image_for_blurred_background_and_overlay(self):
        from PIL import Image
        style = load_style()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            Image.new("RGB", (640, 360), (80, 150, 220)).save(source)
            rendered = render_card({
                "title": "Sự kiện",
                "body": "Tóm tắt ngắn.",
                "image_asset": str(source),
                "image_y": 880,
            }, 1, 1, root / "card.png", style)
            with Image.open(rendered) as image:
                self.assertEqual(image.size, (1080, 1920))

    def test_renderer_refuses_to_overwrite_existing_video(self):
        style = load_style()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "final.mp4"
            target.write_bytes(b"keep")
            result = render_video([], [], Path("missing.wav"), Path("missing.srt"), target, style)
            self.assertEqual(result["status"], "refused")
            self.assertEqual(target.read_bytes(), b"keep")


if __name__ == "__main__":
    unittest.main()

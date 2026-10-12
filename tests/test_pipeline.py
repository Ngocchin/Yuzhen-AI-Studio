import json
import tempfile
import shutil
import subprocess
import unittest
import wave
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from pipeline import __main__ as studio
from pipeline.voice import inspect as inspect_voice, validate_wav
from pipeline import voice


class StudioPipelineTests(unittest.TestCase):
    def test_vietnamese_game_slug(self):
        self.assertEqual(studio.slugify("Liên Quân Mobile"), "lien-quan-mobile")

    def test_subtitle_timestamp(self):
        self.assertEqual(studio.srt_time(65.321), "00:01:05,321")

    def test_entertainment_run_creates_checkpoint_and_artifacts(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(studio, "ROOT", Path(temp)):
            (Path(temp) / "config").mkdir()
            (Path(temp) / "config/defaults.json").write_text(json.dumps({"target_width": 1080, "target_height": 1920, "fps": 30, "meme_pause_seconds": 0.65}))
            result = studio.run(Namespace(game="Liên Quân Mobile", mode="ENTERTAINMENT", voice=None))
            output = Path(temp) / "outputs/lien-quan-mobile"
            checkpoint = json.loads((output / "checkpoint.json").read_text())
            self.assertEqual(result, 0)
            self.assertEqual(checkpoint["mode"], "ENTERTAINMENT")
            self.assertEqual(checkpoint["phases"]["render"]["status"], "blocked")
            self.assertTrue((output / "ideas.json").is_file())
            self.assertEqual(len(json.loads((output / "ideas.json").read_text())), 3)
            self.assertEqual(checkpoint["director"]["execution"], "sequential_checkpointed")

    def test_generated_voice_is_accepted_for_render(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(studio, "ROOT", Path(temp)):
            root = Path(temp)
            (root / "config").mkdir()
            (root / "config/defaults.json").write_text(json.dumps({"target_width": 1080, "target_height": 1920, "fps": 30, "meme_pause_seconds": 0.65}))
            (root / "assets/user").mkdir(parents=True)
            (root / "assets/user/gameplay.mp4").write_bytes(b"test fixture")
            def synthesize_fixture(_text, output):
                with wave.open(str(output), "wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(22050)
                    wav.writeframes(b"\0\0" * 2205)
                return {"status": "generated", "validation": {"status": "validated"}}
            with patch.object(studio, "inspect_voice", return_value={"ready": True}), patch.object(studio, "synthesize", side_effect=synthesize_fixture), patch.object(studio, "render_video", return_value={"status": "rendered", "artifact": "video.mp4"}) as render:
                studio.run(Namespace(game="Liên Quân Mobile", mode="ENTERTAINMENT", voice=None))
            self.assertTrue(render.called)

    def test_news_mode_stops_at_evidence_gate(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(studio, "ROOT", Path(temp)):
            result = studio.run(Namespace(game="Liên Quân Mobile", mode="NEWS", voice=None))
            checkpoint = json.loads((Path(temp) / "outputs/lien-quan-mobile/checkpoint.json").read_text())
            self.assertEqual(result, 2)
            self.assertEqual(checkpoint["status"], "NETWORK_BLOCKED")
            self.assertEqual(checkpoint["director"]["delegated_agent"], "01")

    def test_invalid_wav_is_not_marked_valid(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "broken.wav"
            path.write_bytes(b"not audio")
            result = validate_wav(path)
            self.assertNotEqual(result["status"], "validated")

    def test_valid_wav_passes_ffprobe_when_available(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "tone.wav"
            with wave.open(str(path), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(22050)
                wav.writeframes(b"\0\0" * 2205)
            result = validate_wav(path)
            if result["status"] == "blocked":
                self.skipTest("ffprobe is not installed")
            self.assertEqual(result["status"], "validated")
            self.assertAlmostEqual(result["duration_seconds"], 0.1, places=2)

    def test_director_registry_has_eight_unique_roles(self):
        manifest = json.loads((studio.ROOT / "config/agents.json").read_text())
        roles = manifest["agents"]
        self.assertEqual([role["id"] for role in roles], [f"{i:02}" for i in range(8)])
        self.assertEqual(len({role["name"] for role in roles}), 8)

    def test_model_check_reports_missing_runtime_without_claiming_ready(self):
        result = inspect_voice(model="assets/models/absent.onnx", executable="missing-piper-binary")
        self.assertFalse(result["ready"])

    def test_manual_model_import_keeps_artifacts_outside_git(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            model, config, license_file = root / "voice.onnx", root / "voice.json", root / "LICENSE"
            model.write_bytes(b"model weights")
            config.write_text('{"phoneme_type":"espeak"}')
            license_file.write_text("Example model license")
            with patch.object(voice, "ROOT", root):
                result = voice.import_model(model, config, license_file, "https://voice-publisher.example/model")
            self.assertEqual(result["status"], "imported")
            self.assertTrue((root / "assets/models/MODEL-LICENSE.txt").is_file())
            self.assertIn("assets/models/", (studio.ROOT / ".gitignore").read_text())

    def test_ffmpeg_render_and_ffprobe_qc_end_to_end(self):
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg or not shutil.which("ffprobe"):
            self.skipTest("FFmpeg and ffprobe are required")
        with tempfile.TemporaryDirectory() as temp, patch.object(studio, "ROOT", Path(temp)):
            root = Path(temp)
            gameplay = root / "gameplay.mp4"
            voice = root / "voice.wav"
            sfx = root / "assets/user/meme-sfx.wav"
            sfx.parent.mkdir(parents=True)
            subprocess.run([ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=blue:s=180x320:r=12:d=2", "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(gameplay)], check=True, capture_output=True)
            subprocess.run([ffmpeg, "-y", "-f", "lavfi", "-i", "sine=frequency=660:duration=2", str(voice)], check=True, capture_output=True)
            subprocess.run([ffmpeg, "-y", "-f", "lavfi", "-i", "sine=frequency=880:duration=0.25", str(sfx)], check=True, capture_output=True)
            script = {"duration_seconds": 1.3, "meme_beat_seconds": 0.5, "voiceover": [{"start": 0, "end": 0.5, "text": "Xin chào"}, {"start": 0.5, "end": 1.3, "text": "Đang giao tranh"}]}
            settings = {"target_width": 1080, "target_height": 1920, "fps": 12, "meme_pause_seconds": 0.2}
            rendered = studio.render_video(gameplay, voice, root / "outputs/sample", script, settings)
            self.assertEqual(rendered["status"], "rendered", rendered)
            qc = studio.quality_control(root / "outputs/sample/video.mp4", 1.5)
            self.assertEqual(qc["status"], "passed", qc)
            self.assertTrue(rendered["sfx_included"])


if __name__ == "__main__":
    unittest.main()

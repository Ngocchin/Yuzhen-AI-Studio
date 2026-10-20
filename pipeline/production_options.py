"""Explicit Option B for the already approved Production #003 AWC 2019 script."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from pipeline.event_storytelling import DEFAULT_STYLE, load_style, render_card, render_video
from pipeline.voice import validate_wav

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = ROOT / "outputs/production-003-awc-2019"
OFFICIAL_RECAP = "https://moba.garena.tw/news/show/1888"


def _scenes() -> list[dict]:
    disclosure = "MINH HỌA · KHÔNG PHẢI GAMEPLAY"
    return [
        {"start": 0, "end": 2.98, "beat": "HOOK", "title": "CHUNG KẾT TỚI VÁN 7", "body": "Một chiếc cúp. Hai đội. Câu trả lời nằm ở ván cuối.", "callout": "AWC 2019 · BO7", "diagram": {"kind": "series_score", "items": [{"label": "CHUNG KẾT AWC 2019", "value": "BO7"}, {"label": "KẾT QUẢ", "value": "4–3"}]}, "disclosure": disclosure, "source": "FACT: GARENA TAIWAN · ORIGINAL GRAPHIC"},
        {"start": 2.98, "end": 8.06, "beat": "SETUP", "title": "VIỆT NAM × ĐÀI BẮC TRUNG HOA", "body": "Team Flash gặp MAD Team tại Đà Nẵng.", "callout": "14.07.2019 · AWC WORLD CUP", "diagram": {"kind": "event_timeline", "items": [{"label": "VIỆT NAM", "value": "TEAM FLASH"}, {"label": "ĐÀ NẴNG", "value": "AWC 2019"}, {"label": "GCS", "value": "MAD TEAM"}]}, "disclosure": disclosure, "source": "FACT: GARENA TAIWAN · ORIGINAL GRAPHIC"},
        {"start": 8.06, "end": 15.47, "beat": "CONFLICT", "title": "SÁU VÁN VẪN CHƯA XONG", "body": "Loạt BO7 kéo tới thế cân bằng trước ván quyết định.", "callout": "3–3 SAU 6 VÁN · SUY RA TỪ TỶ SỐ CHUNG CUỘC", "diagram": {"kind": "series_progress", "items": [{"label": "SAU 6 VÁN", "value": "3–3"}, {"label": "CÒN LẠI", "value": "VÁN 7"}]}, "disclosure": disclosure, "source": "FACT + ARITHMETIC INFERENCE · OFFICIAL SCORE"},
        {"start": 15.47, "end": 16.12, "beat": "BREATH", "title": "VÁN CUỐI", "body": "Một nhịp dừng trước cao trào.", "callout": "MINH HỌA BIÊN TẬP", "disclosure": disclosure, "source": "ORIGINAL GRAPHIC"},
        {"start": 16.12, "end": 22.04, "beat": "CLIMAX", "title": "ĐIỂM NGOẶT Ở ĐƯỜNG GIỮA", "body": "Phút 18: Team Flash thắng giao tranh 0 đổi 3 rồi ăn Caesar.", "callout": "SƠ ĐỒ DIỄN BIẾN · KHÔNG PHẢI BẢN ĐỒ TRẬN ĐẤU", "diagram": {"kind": "battle_flow", "items": [{"label": "18 PHÚT", "detail": "GIỮA"}, {"label": "0 ĐỔI 3", "detail": "GIAO TRANH"}, {"label": "CAESAR", "detail": "LẤY MỤC TIÊU"}]}, "disclosure": disclosure, "source": "FACT: GARENA TAIWAN · ORIGINAL DIAGRAM"},
        {"start": 22.04, "end": 28.45, "beat": "PAYOFF", "title": "CƠ HỘI CUỐI MỞ RA", "body": "Khoảng phút 20, Team Flash phá nhà chính và chốt chức vô địch 4–3.", "callout": "AWC 2019 · TEAM FLASH VÔ ĐỊCH", "diagram": {"kind": "event_timeline", "items": [{"label": "18'", "value": "GIAO TRANH"}, {"label": "20'", "value": "ĐẨY CAO"}, {"label": "4–3", "value": "KẾT THÚC"}]}, "disclosure": disclosure, "source": "FACT: GARENA TAIWAN · ORIGINAL GRAPHIC"},
        {"start": 28.45, "end": 29.10, "beat": "MEME_PAUSE", "title": "DỪNG NỬA NHỊP", "body": "Khoảng nghỉ tự nhiên của voice.", "callout": "0,65 GIÂY · KHÔNG SFX", "disclosure": disclosure, "source": "ORIGINAL GRAPHIC"},
        {"start": 29.10, "end": 33.82, "beat": "ENDING", "title": "MỘT VÁN PHÂN ĐỊNH TẤT CẢ", "body": "Team Flash thắng loạt trận 4–3. Anh em còn nhớ trận BO7 nào hồi hộp tới phút cuối?", "callout": "TEAM FLASH 4 — 3 MAD TEAM", "diagram": {"kind": "series_score", "items": [{"label": "VIỆT NAM · TEAM FLASH", "value": "4"}, {"label": "MAD TEAM · GCS", "value": "3"}]}, "disclosure": disclosure, "source": "FACT: GARENA TAIWAN · ORIGINAL GRAPHIC"},
        {"start": 33.82, "end": 35.22, "beat": "END_CARD_HOLD", "title": "YUZHEN CHƠI GÌ", "body": "Kể chuyện game · Chờ bạn bình luận", "callout": "SOURCE: GARENA TAIWAN OFFICIAL RECAP", "disclosure": disclosure, "source": OFFICIAL_RECAP},
    ]


def build_option_b(production: Path = PRODUCTION) -> dict:
    production = Path(production)
    original_storyboard = production / "storyboard.json"
    original_checkpoint = production / "checkpoint.json"
    audio = production / "voice-minh-quan.wav"
    for required in (original_storyboard, original_checkpoint, audio):
        if not required.is_file():
            return {"status": "blocked", "reason": f"Required preserved Production #003 file missing: {required.name}"}
    checkpoint = json.loads(original_checkpoint.read_text(encoding="utf-8"))
    voice = checkpoint.get("voice", {})
    voice_config = json.loads((ROOT / "config/voice.json").read_text(encoding="utf-8"))
    if voice.get("engine") != "VieNeu-TTS" or voice.get("version") != "3.7.1" or voice.get("preset") != "Minh Quân" or voice_config.get("selected_vieneu_voice") != "Minh Quân":
        return {"status": "blocked", "reason": "Production #003 approved voice identity does not match Minh Quân / VieNeu-TTS 3.7.1."}
    audio_check = validate_wav(audio)
    if audio_check.get("status") != "validated" or abs(audio_check["duration_seconds"] - 33.82) > 0.15:
        return {"status": "blocked", "reason": "Preserved approved voice WAV is not a valid 33.82-second file.", "voice_check": audio_check}

    option_dir = production / "option-b"
    output = option_dir / "option-b.mp4"
    storyboard_path = option_dir / "storyboard.json"
    srt_path = option_dir / "captions.srt"
    card_dir = option_dir / "scene-cards"
    thumbnail = option_dir / "thumbnail.png"
    reserved = (output, storyboard_path, srt_path, card_dir, thumbnail)
    existing = [str(p) for p in reserved if p.exists()]
    if existing:
        return {"status": "refused", "reason": "Option B has existing output; refusing to overwrite.", "existing": existing}

    scenes = _scenes()
    if round(scenes[-1]["end"] - scenes[0]["start"], 2) != 35.22:
        return {"status": "failed", "reason": "Option B scene timing must be 35.22 seconds."}
    storyboard = {
        "production_id": "Production #003",
        "option": "B",
        "claim_type": "REAL_MATCH",
        "render_status": "ORIGINAL_EDITORIAL_ILLUSTRATION",
        "do_not_present_graphics_as_gameplay": True,
        "voice_preserved": {"file": "../voice-minh-quan.wav", "engine": "VieNeu-TTS", "version": "3.7.1", "preset": "Minh Quân", "duration_seconds": 33.82},
        "visual_notice": "Every graphic is original editorial illustration. No footage, screenshot, game UI, character art, or broadcast asset is represented.",
        "scenes": scenes,
        "source_facts": [OFFICIAL_RECAP],
    }
    option_dir.mkdir(parents=True, exist_ok=True)
    storyboard_path.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    srt_rows = []
    index = 1
    for scene in scenes:
        line = next((s for s in json.loads(original_storyboard.read_text(encoding="utf-8"))["scenes"] if s["beat"] == scene["beat"]), None)
        caption = line.get("voice_text", "") if line else ""
        if caption:
            srt_rows.append(f"{index}\n{_srt(scene['start'])} --> {_srt(scene['end'])}\n{caption}\n")
            index += 1
    srt_path.write_text("\n".join(srt_rows), encoding="utf-8")

    style = load_style(DEFAULT_STYLE)
    cards, durations = [], []
    for i, scene in enumerate(scenes, 1):
        card = card_dir / f"card-{i:02d}.png"
        render_card(scene, i, len(scenes), card, style)
        cards.append(card)
        durations.append(round(scene["end"] - scene["start"], 4))
    shutil.copy2(cards[0], thumbnail)
    result = render_video(cards, durations, audio, srt_path, output, style, audio_tail_pad_seconds=1.4)
    if result.get("status") != "rendered":
        return {"status": result.get("status", "failed"), "reason": result.get("reason", result.get("detail", "Render failed")), "detail": result.get("detail")}
    qc = _qc(output)
    metadata = {
        "production_id": "Production #003",
        "option_a": {"status": "NEEDS_LICENSE", "requires": ["permission covering match broadcast", "underlying game footage rights", "editing", "TikTok/YouTube Shorts posting", "commercial/monetized use if intended"]},
        "option_b": {"status": "READY_FOR_REVIEW" if qc.get("status") == "passed" else "QC_FAILED", "visual_style": "Original timeline and battle-flow diagrams; not gameplay", "voice": "Minh Quân · VieNeu-TTS 3.7.1", "duration_seconds": qc.get("duration_seconds"), "qc": qc},
        "source": {"url": OFFICIAL_RECAP, "owner": "Garena Taiwan", "use": "Fact verification only; no source artwork or footage included."},
        "human_review_required": ["Listen to narration/caption sync", "Approve infographic-only visual style in place of gameplay", "Review highlighted match facts and disclosure"],
    }
    (option_dir / "options.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "rendered" if qc.get("status") == "passed" else "qc_failed", "video": str(output), "thumbnail": str(thumbnail), "captions": str(srt_path), "options": metadata}


def _srt(seconds: float) -> str:
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def _qc(video: Path) -> dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return {"status": "blocked", "reason": "ffprobe unavailable"}
    result = subprocess.run([ffprobe, "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,duration", "-show_entries", "format=duration,size", "-of", "json", str(video)], capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
        streams = data["streams"]
        picture = next(s for s in streams if s["codec_type"] == "video")
        audio = next(s for s in streams if s["codec_type"] == "audio")
        duration = float(data["format"]["duration"])
        checks = {
            "video_1080x1920": picture.get("width") == 1080 and picture.get("height") == 1920,
            "audio_present": audio.get("codec_type") == "audio",
            "duration_35_22_seconds": abs(duration - 35.22) < 0.15,
            "file_nonempty": video.is_file() and video.stat().st_size > 10000,
        }
        return {"status": "passed" if all(checks.values()) else "failed", "checks": checks, "duration_seconds": duration, "size_bytes": int(data["format"].get("size", 0)), "audio_codec": audio.get("codec_name")}
    except (KeyError, StopIteration, ValueError, json.JSONDecodeError):
        return {"status": "failed", "reason": result.stderr.strip() or "Invalid FFprobe output"}


def main() -> int:
    result = build_option_b()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "rendered" else 2


if __name__ == "__main__":
    raise SystemExit(main())

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from pipeline.voice_router import inspect as inspect_voice, synthesize
from pipeline.voice import validate_wav
from pipeline import story_strategy

ROOT = Path(__file__).resolve().parents[1]


def slugify(value):
    import unicodedata
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-") or "game"


def run(args):
    slug = slugify(args.game)
    out = ROOT / "outputs" / slug
    out.mkdir(parents=True, exist_ok=True)
    checkpoint_path = out / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text()) if checkpoint_path.exists() else {
        "game": args.game, "mode": args.mode, "phases": {}, "created_at": datetime.now(timezone.utc).isoformat()
    }
    if checkpoint.get("mode") != args.mode:
        checkpoint["phases"] = {}
    checkpoint["mode"] = args.mode
    policy = story_strategy.load_config()
    checkpoint["content_strategy"] = {"config": "config/content-strategy.json", "story_first": policy["story_first"], "voice_engine": policy["voice"]["engine"], "voice_version": policy["voice"]["version"], "voice_preset": policy["voice"]["preset"]}
    if args.mode == "NEWS":
        checkpoint["status"] = "NETWORK_BLOCKED"
        checkpoint["phases"]["trend_hunter"] = {"status": "NETWORK_BLOCKED", "reason": "No verified source records or network research configured."}
        checkpoint["director"] = {"status": "stopped_at_evidence_gate", "delegated_agent": "01", "execution": "sequential_checkpointed"}
        save(checkpoint_path, checkpoint)
        print("NEWS mode: NETWORK_BLOCKED; no news claim generated.")
        return 2

    ideas = [
        {"title": "Đợi farm thêm một món thì combat nổ", "premise": "Một tình huống tổng hợp hư cấu: xạ thủ xin thêm một đợt lính; cả đội mở combat.", "category": "GAME", "claim_type": "FICTION", "storytelling_dimensions": {"story_appeal": 21, "conflict_mystery_climax": 16, "curiosity_hook": 19, "emotion_debate": 13, "gaming_community_fit": 9, "rights_cleared_media_feasibility": 9}, "viral_potential_score": 88},
        {"title": "Ping rút lui nhưng chân tự lao vào", "premise": "Tình huống tổng hợp hư cấu: miệng bảo rút nhưng nhân vật lao theo đồng đội.", "category": "GAME", "claim_type": "FICTION", "storytelling_dimensions": {"story_appeal": 20, "conflict_mystery_climax": 17, "curiosity_hook": 18, "emotion_debate": 12, "gaming_community_fit": 9, "rights_cleared_media_feasibility": 9}, "viral_potential_score": 84},
        {"title": "Đồng đội bảo giữ chiêu cuối", "premise": "Tình huống tổng hợp hư cấu: người chơi giữ chiêu cuối tới lúc trận đấu kết thúc.", "category": "GAME", "claim_type": "FICTION", "storytelling_dimensions": {"story_appeal": 19, "conflict_mystery_climax": 15, "curiosity_hook": 17, "emotion_debate": 12, "gaming_community_fit": 9, "rights_cleared_media_feasibility": 8}, "viral_potential_score": 80}
    ]
    for idea in ideas:
        decision = story_strategy.topic_decision({**idea, "story_angle": idea["premise"]})
        idea["storytelling_score"] = story_strategy.storytelling_score(idea["storytelling_dimensions"])
        idea["combined_priority_score"] = story_strategy.rank_score(idea["storytelling_score"], idea["viral_potential_score"])
        idea["qualified_for_shortlist"] = decision["eligible"] and idea["storytelling_score"] >= policy["storytelling_score"]["minimum"]
        idea["claim_note"] = "Composite fictional scenario; not a report of a real match."
    script = {
      "title": ideas[0]["title"], "duration_seconds": 42,
      "voiceover": [
        {"start": 0.0, "end": 4.0, "text": "Anh em biết cái câu: đợi mình farm thêm một món không?"},
        {"start": 4.0, "end": 10.0, "text": "Mình vừa ping: đừng combat nha, xạ thủ còn thiếu đúng một cây kiếm."},
        {"start": 10.0, "end": 16.0, "text": "Chớp mắt một cái, đường giữa lao lên như vừa trúng số."},
        {"start": 16.0, "end": 21.0, "text": "Rừng ping giao tranh. Trợ thủ mở chiêu. Mình thì đang đánh con lính cuối."},
        {"start": 21.0, "end": 27.0, "text": "Thế là phải bỏ lính, tốc biến vào giữa đội hình, tay bấm kỹ năng theo bản năng."},
        {"start": 27.0, "end": 34.0, "text": "Combat xong, cả đội nằm hết. Mình sống sót với một món đồ và một đống câu hỏi."},
        {"start": 34.0, "end": 42.0, "text": "Bài học hôm nay: farm thêm món thì được, nhớ nhìn bản đồ trước nha!"}
      ],
      "meme_beat_seconds": 21.0,
      "scenes": [
        {"start": 0, "end": 4, "visual": "Cận cảnh bảng trang bị còn thiếu một món", "sfx": "nhạc căng nhẹ"},
        {"start": 4, "end": 10, "visual": "Gameplay: ping lùi và lính đang thấp máu", "sfx": "ping"},
        {"start": 10, "end": 16, "visual": "Gameplay: đồng đội bất ngờ lao vào", "sfx": "whoosh"},
        {"start": 16, "end": 21, "visual": "Gameplay: giao tranh nổ trong lúc đang farm", "sfx": "combat SFX"},
        {"start": 21, "end": 24, "visual": "Reaction meme do người dùng cung cấp", "sfx": "meme SFX; ngắt narration 0,65 giây"},
        {"start": 24, "end": 34, "visual": "Gameplay: hỗn loạn rồi màn hình hồi sinh", "sfx": "combat giảm dần"},
        {"start": 34, "end": 42, "visual": "Bảng trang bị hoàn chỉnh, CTA hỏi khán giả", "sfx": "nhạc kết"}
      ]
    }
    save(out / "ideas.json", ideas)
    save(out / "script.json", script)
    save(out / "storyboard.json", {"game": args.game, "scenes": script["scenes"], "format": "1080x1920, 9:16"})
    save(out / "channel-copy.json", {"tiktok_title": "Farm thêm một món thôi mà combat nổ luôn 😭", "shorts_title": "Đợi farm thêm một món thì combat nổ | Liên Quân", "caption": "Bạn đã từng xin farm thêm rồi combat nổ chưa?", "hashtags": ["#LienQuanMobile", "#Gaming", "#YuzhenChoiGi", "#GameHai"], "thumbnail": "Gameplay giao tranh, nhân vật đang farm, chữ lớn: CÒN 1 MÓN!"})
    checkpoint["phases"].update({"ideas": {"status": "complete", "artifact": "ideas.json"}, "script": {"status": "complete", "artifact": "script.json"}, "storyboard": {"status": "complete", "artifact": "storyboard.json"}, "channel_manager": {"status": "complete", "artifact": "channel-copy.json"}})
    settings = json.loads((ROOT / "config/defaults.json").read_text())

    voice = Path(args.voice).expanduser() if args.voice else None
    if voice and voice.exists():
        checkpoint["phases"]["voice"] = validate_wav(voice)
        if checkpoint["phases"]["voice"]["status"] == "validated": checkpoint["phases"]["voice"]["status"] = "validated"
    elif inspect_voice()["ready"]:
        # One real synthesis attempt; output is accepted only after Piper and ffprobe both succeed.
        voice = out / "voice.wav"
        text = " ".join(line["text"] for line in script["voiceover"])
        checkpoint["phases"]["voice"] = synthesize(text, voice)
    else:
        checkpoint["phases"]["voice"] = {"status": "blocked", "reason": "Piper executable and/or vi_VN-vais1000-medium ONNX model plus JSON config unavailable.", "readiness": inspect_voice()}

    gameplay = ROOT / "assets/user/gameplay.mp4"
    checkpoint["phases"]["render"] = {"status": "blocked", "missing": []}
    if not gameplay.exists(): checkpoint["phases"]["render"]["missing"].append(str(gameplay.relative_to(ROOT)))
    if not voice or not voice.exists() or checkpoint["phases"]["voice"].get("status") not in ("validated", "generated"): checkpoint["phases"]["render"]["missing"].append("validated voice WAV")
    if checkpoint["phases"]["render"]["missing"]:
        checkpoint["phases"]["render"]["reason"] = "Rendering requires rights-cleared gameplay and a real voice WAV; no MP4 was claimed."
    else:
        rendered = render_video(gameplay, voice, out, script, settings)
        checkpoint["phases"]["render"] = rendered
        if rendered["status"] == "rendered":
            checkpoint["phases"]["quality_control"] = quality_control(out / "video.mp4", script["duration_seconds"] + settings["meme_pause_seconds"])
    checkpoint["status"] = "checkpoint_saved"
    checkpoint["director"] = {
        "status": "complete_with_blocked_phases" if checkpoint["phases"].get("render", {}).get("status") == "blocked" or checkpoint["phases"].get("voice", {}).get("status") == "blocked" else "complete",
        "execution": "sequential_checkpointed",
        "role_status": {
            "00": "complete", "01": "not_required_entertainment", "02": checkpoint["phases"]["ideas"]["status"],
            "03": checkpoint["phases"]["script"]["status"], "04": checkpoint["phases"]["voice"]["status"],
            "05": checkpoint["phases"]["render"]["status"], "06": checkpoint["phases"].get("quality_control", {}).get("status", "waiting_for_render"),
            "07": checkpoint["phases"]["channel_manager"]["status"]
        }
    }
    save(checkpoint_path, checkpoint)
    print(f"Production checkpoint: {out.relative_to(ROOT)}")
    for name, phase in checkpoint["phases"].items(): print(f"{name}: {phase['status']}")
    return 0


def srt_time(seconds):
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def render_video(gameplay, voice, out, script, settings):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return {"status": "blocked", "reason": "ffmpeg unavailable"}
    out.mkdir(parents=True, exist_ok=True)
    srt = out / "subtitles.srt"
    entries = []
    pause_at = script["meme_beat_seconds"]
    pause_duration = settings["meme_pause_seconds"]
    for index, line in enumerate(script["voiceover"], 1):
        start = line["start"] + (pause_duration if line["start"] >= pause_at else 0)
        end = line["end"] + (pause_duration if line["end"] > pause_at else 0)
        entries.append(f"{index}\n{srt_time(start)} --> {srt_time(end)}\n{line['text']}\n")
    srt.write_text("\n".join(entries), encoding="utf-8")
    sfx = ROOT / "assets/user/meme-sfx.wav"
    music = ROOT / "assets/user/music.wav"
    inputs = ["-i", str(gameplay), "-i", str(voice)]
    if sfx.exists(): inputs += ["-i", str(sfx)]
    if music.exists(): inputs += ["-i", str(music)]
    # Keep the source game capture intact apart from proportional crop/scale to the requested canvas.
    subtitle_path = str(srt).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    width, height = settings["target_width"], settings["target_height"]
    video_filter = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},subtitles='{subtitle_path}'"
    audio_parts = [f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,atrim=start=0:end={pause_at},asetpts=PTS-STARTPTS[before];anullsrc=channel_layout=stereo:sample_rate=48000:d={pause_duration}[gap];[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,atrim=start={pause_at},asetpts=PTS-STARTPTS[after];[before][gap][after]concat=n=3:v=0:a=1[voice]"]
    mix = "[voice]"
    next_input = 2
    if sfx.exists():
        delay = round(pause_at * 1000)
        audio_parts.append(f"[{next_input}:a]adelay={delay}|{delay},volume=1[sfx]")
        mix = "[voice][sfx]"
        next_input += 1
    if music.exists():
        audio_parts.append(f"[{next_input}:a]volume=0.12[music]")
        mix += "[music]"
    if len(mix) > len("[voice]"):
        audio_parts.append(f"{mix}amix=inputs={mix.count('[')}:duration=first:dropout_transition=2[outa]")
        audio_map = "[outa]"
    else:
        audio_map = "1:a"
    graph = f"[0:v]{video_filter}[outv];" + ";".join(audio_parts)
    target = out / "video.mp4"
    expected_duration = script["duration_seconds"] + pause_duration
    cmd = [ffmpeg, "-y", *inputs, "-filter_complex", graph, "-map", "[outv]", "-map", audio_map, "-t", str(expected_duration), "-r", str(settings["fps"]), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", str(target)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode or not target.exists():
        return {"status": "failed", "detail": result.stderr[-1500:]}
    return {"status": "rendered", "artifact": str(target.relative_to(ROOT)), "meme_pause_seconds": pause_duration, "sfx_included": sfx.exists(), "music_included": music.exists()}


def quality_control(video, expected_duration):
    probe = shutil.which("ffprobe")
    if not probe:
        return {"status": "blocked", "reason": "ffprobe unavailable; media cannot be inspected."}
    result = subprocess.run([probe, "-v", "error", "-show_entries", "stream=codec_type,width,height", "-show_entries", "format=duration", "-of", "json", str(video)], capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        v = next(s for s in streams if s.get("codec_type") == "video")
        has_audio = any(s.get("codec_type") == "audio" for s in streams)
        duration = float(data.get("format", {}).get("duration", 0))
        checks = {"resolution_1080x1920": v.get("width") == 1080 and v.get("height") == 1920, "audio_present": has_audio, "duration_within_2s": abs(duration - expected_duration) <= 2}
        return {"status": "passed" if all(checks.values()) else "failed", "checks": checks, "duration_seconds": duration, "human_review_required": ["Listen for voice quality and SFX clarity", "Watch for black frames, subtitle timing/readability, and acceptable source rights"]}
    except (ValueError, StopIteration, json.JSONDecodeError):
        return {"status": "failed", "reason": "Unable to inspect rendered media with ffprobe."}


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Yuzhen AI Studio local production pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("run", help="produce an entertainment checkpoint or check news mode")
    command.add_argument("--game", required=True)
    command.add_argument("--mode", choices=("ENTERTAINMENT", "NEWS"), default="ENTERTAINMENT")
    command.add_argument("--voice", help="existing voice WAV")
    args = parser.parse_args()
    sys.exit(run(args))


if __name__ == "__main__": main()

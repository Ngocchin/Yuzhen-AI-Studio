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
from pipeline.media_feasibility import score_media_feasibility
from pipeline.topic_queue import record_waiting_topic
from pipeline.media_sources import classify_source
from pipeline.real_footage import preflight_real_footage
from pipeline.topic_queue import DEFAULT_SOURCE_LEDGER, filter_previously_rejected, record_source_decision

ROOT = Path(__file__).resolve().parents[1]


def run_real_footage(args):
    """Run a separate real-footage-first preflight without touching older outputs."""
    output = Path(getattr(args, "output_dir", None) or ROOT / "outputs/production-004-real-footage")
    output = output if output.is_absolute() else ROOT / output
    storyboard_path = Path(getattr(args, "storyboard", None) or ROOT / "outputs/production-004/storyboard.json")
    storyboard_path = storyboard_path if storyboard_path.is_absolute() else ROOT / storyboard_path
    candidates_path = Path(getattr(args, "candidates", None) or output / "candidates.json")
    candidates_path = candidates_path if candidates_path.is_absolute() else ROOT / candidates_path
    mode = getattr(args, "output_mode", "SAFE")
    targets = [output / name for name in ("edit-plan.json", "edit-plan.md", "checkpoint.json")]
    existing = [str(path) for path in targets if path.exists()]
    if existing:
        print(f"Refusing to overwrite real-footage checkpoint artifacts: {existing}")
        return 2
    if not storyboard_path.is_file() or not candidates_path.is_file():
        print("REAL_FOOTAGE_FIRST requires existing storyboard and candidate-manifest files.")
        return 2
    story = json.loads(storyboard_path.read_text(encoding="utf-8"))
    manifest = json.loads(candidates_path.read_text(encoding="utf-8"))
    candidates = manifest.get("candidates", [])
    ledger = json.loads(DEFAULT_SOURCE_LEDGER.read_text(encoding="utf-8")) if DEFAULT_SOURCE_LEDGER.exists() else {"rejected_source_keys": []}
    candidates = filter_previously_rejected(candidates, ledger)
    result = preflight_real_footage(
        story.get("scenes", []), candidates, mode=mode, production_dir=ROOT,
        expected_game=manifest.get("game", "Arena of Valor"),
    )
    output.mkdir(parents=True, exist_ok=True)
    result["production_id"] = manifest.get("production_id", "Production #004")
    result["source_candidate_count"] = len(candidates)
    (output / "edit-plan.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Production #004 — REAL_FOOTAGE_FIRST edit plan", "", f"**Mode:** {mode}", f"**Status:** {result['status']}", "", "| Scene | Candidate | Footage URL | Timecode | Rights | Confidence | Match |", "|---|---|---|---|---|---|---|"]
    for row in result["scene_matches"]:
        tc = row.get("timecode")
        tc_text = f"{tc['in_seconds']:.2f}–{tc['out_seconds']:.2f}s" if tc else "Not verified"
        lines.append("| {scene} | {candidate} | {url} | {tc} | {rights} | {confidence} | {match} |".format(
            scene=row.get("scene_id", ""), candidate=row.get("title") or row.get("candidate_id") or "—",
            url=row.get("url") or "—", tc=tc_text, rights=row.get("rights_status") or "—",
            confidence=row.get("confidence", "NONE"), match=(row.get("editorial_match") or row.get("missing_reason", "")).replace("|", "/"),
        ))
    lines += ["", "No clip is rendered from discovery metadata. A local library file, verified scene/game identity, rights evidence, and reviewed timecode are required.", ""]
    (output / "edit-plan.md").write_text("\n".join(lines), encoding="utf-8")
    for candidate in candidates:
        decision = classify_source(candidate)
        if candidate.get("source_url"):
            record_source_decision(
                candidate["source_url"], decision["status"], decision["reason"],
                category=decision["category"],
                supporting_factors=decision.get("supporting_factors", []),
                opposing_factors=decision.get("opposing_factors", []),
            )
    checkpoint = {
        "production_id": result["production_id"], "mode": "REAL_FOOTAGE_FIRST", "output_mode": mode,
        "status": result["status"], "may_render": result["may_render"],
        "voice_source": "../production-004/voice-minh-quan.wav (existing, unchanged)",
        "previous_production_preserved": True,
        "phases": {"candidate_search": "complete", "rights_preflight": result["status"], "render": "blocked_missing_permitted_footage" if not result["may_render"] else "ready"},
    }
    (output / "checkpoint.json").write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"REAL_FOOTAGE_FIRST: {result['status']}; candidates={len(candidates)}; missing scenes={len(result['missing_scene_ids'])}")
    return 0 if result["may_render"] else 2


def slugify(value):
    import unicodedata
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-") or "game"


def run(args):
    if args.mode == "REAL_FOOTAGE_FIRST":
        return run_real_footage(args)
    slug = slugify(args.game)
    out = ROOT / "outputs" / slug
    if out.exists() and any(out.iterdir()):
        base = out
        counter = 2
        while out.exists():
            out = base.with_name(f"{base.name}-production-{counter:03d}")
            counter += 1
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
        {"title": "Đợi farm thêm một món thì combat nổ", "premise": "Một tình huống tổng hợp hư cấu: xạ thủ xin thêm một đợt lính; cả đội mở combat.", "category": "GAME", "claim_type": "FICTION", "storytelling_dimensions": {"story_appeal": 21, "conflict_mystery_climax": 16, "curiosity_hook": 19, "emotion_debate": 13, "gaming_community_fit": 9, "narrative_originality_and_clarity": 9}, "viral_potential_score": 88},
        {"title": "Ping rút lui nhưng chân tự lao vào", "premise": "Một tình huống tổng hợp hư cấu: miệng bảo rút nhưng nhân vật lao theo đồng đội.", "category": "GAME", "claim_type": "FICTION", "storytelling_dimensions": {"story_appeal": 20, "conflict_mystery_climax": 17, "curiosity_hook": 18, "emotion_debate": 12, "gaming_community_fit": 9, "narrative_originality_and_clarity": 9}, "viral_potential_score": 84},
        {"title": "Đồng đội bảo giữ chiêu cuối", "premise": "Một tình huống tổng hợp hư cấu: người chơi giữ chiêu cuối tới lúc trận đấu kết thúc.", "category": "GAME", "claim_type": "FICTION", "storytelling_dimensions": {"story_appeal": 19, "conflict_mystery_climax": 15, "curiosity_hook": 17, "emotion_debate": 12, "gaming_community_fit": 9, "narrative_originality_and_clarity": 8}, "viral_potential_score": 80}
    ]
    for idea in ideas:
        decision = story_strategy.topic_decision({**idea, "story_angle": idea["premise"]})
        idea["storytelling_score"] = story_strategy.storytelling_score(idea["storytelling_dimensions"])
        scene_plan = [{"id": f"scene-{n}", "visual_plan": "clearly_labeled_fiction_graphic", "claim_type": "FICTION", "uses_third_party_art": False, "clearly_labeled_as_illustration": True} for n in range(1, 6)]
        idea["media_feasibility"] = score_media_feasibility(scene_plan)
        idea["media_feasibility_score"] = idea["media_feasibility"]["score"]
        idea["production_priority_score"] = story_strategy.production_priority_score(idea["storytelling_score"], idea["viral_potential_score"], idea["media_feasibility_score"])
        idea["combined_priority_score"] = idea["production_priority_score"]
        idea["qualified_for_shortlist"] = decision["eligible"] and idea["storytelling_score"] >= policy["storytelling_score"]["minimum"]
        idea["claim_note"] = "Composite fictional scenario; not a report of a real match."
    selection = story_strategy.choose_production_topic(ideas)
    ideas = selection["ranked"] + [item for item in ideas if item not in selection["ranked"]]
    for item in selection["waiting"]:
        record_waiting_topic({"title": item["title"], "storytelling_score": item["storytelling_score"], "viral_potential_score": item["viral_potential_score"], "media_feasibility_score": item["media_feasibility_score"]}, out.parent / "topic-backlog.json")
    if selection["production_blocked"]:
        save(out / "ideas.json", ideas)
        checkpoint["phases"].update({"ideas": {"status": "complete", "artifact": "ideas.json"}, "media": {"status": "waiting_for_media", "backlog": "../topic-backlog.json", "reason": "No Story-qualified topic meets the configured Media Feasibility threshold."}})
        checkpoint["status"] = "WAITING_FOR_MEDIA"
        checkpoint["director"] = {"status": "waiting_for_media", "execution": "sequential_checkpointed", "selected_topic": None}
        save(checkpoint_path, checkpoint)
        print("No production-ready story met the Media Feasibility threshold; qualified ideas were added to the waiting queue.")
        return 2
    selected = selection["selected"]
    script = {
      "title": selected["title"], "duration_seconds": 42, "claim_type": selected["claim_type"],
      "source_urls": selected.get("sources", []),
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
        {"start": 0, "end": 4, "beat": "HOOK", "visual": "Minh họa một ô trang bị còn thiếu cạnh đợt lính"},
        {"start": 4, "end": 10, "beat": "SETUP", "visual": "Sơ đồ ping lùi và đợt lính thấp máu"},
        {"start": 10, "end": 16, "beat": "CONFLICT", "visual": "Sơ đồ mũi tên: đồng đội bất ngờ mở giao tranh"},
        {"start": 16, "end": 21, "beat": "CLIMAX", "visual": "Sơ đồ diễn biến giao tranh khi xạ thủ còn farm"},
        {"start": 21, "end": 24, "beat": "MEME", "visual": "Reaction tự vẽ, không dùng meme của creator khác"},
        {"start": 24, "end": 34, "beat": "PAYOFF", "visual": "Thẻ kết quả hư cấu, không mô phỏng giao diện hồi sinh"},
        {"start": 34, "end": 42, "beat": "ENDING", "visual": "Infographic kết và câu hỏi khán giả"}
      ]
    }
    save(out / "ideas.json", ideas)
    save(out / "script.json", script)
    save(out / "storyboard.json", {"game": args.game, "scenes": script["scenes"], "format": "1080x1920, 9:16"})
    save(out / "channel-copy.json", {"tiktok_title": "Farm thêm một món thôi mà combat nổ luôn 😭", "shorts_title": "Đợi farm thêm một món thì combat nổ | Liên Quân", "caption": "Bạn đã từng xin farm thêm rồi combat nổ chưa?", "hashtags": ["#LienQuanMobile", "#Gaming", "#YuzhenChoiGi", "#GameHai"], "thumbnail": "Original illustrated farm-versus-teamfight diagram, labeled as illustration; text: CÒN 1 MÓN!"})
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
    rights_file = ROOT / "assets/user/media-rights.json"
    rights_record = json.loads(rights_file.read_text(encoding="utf-8")) if rights_file.is_file() else {}
    gameplay_rights = (rights_record.get("assets") or {}).get("gameplay.mp4", {})
    gameplay_authorized = gameplay.exists() and classify_source(gameplay_rights).get("status") == "AUTHORIZED"
    authorized_optional_audio = {
        filename for filename in ("meme-sfx.wav", "music.wav")
        if classify_source((rights_record.get("assets") or {}).get(filename, {})).get("status") == "AUTHORIZED"
    }
    if not voice or not voice.exists() or checkpoint["phases"]["voice"].get("status") not in ("validated", "generated"):
        checkpoint["phases"]["render"] = {"status": "blocked", "reason": "A real, ffprobe-validated voice WAV is required."}
    elif gameplay_authorized:
        rendered = render_video(gameplay, voice, out, script, settings, authorized_optional_audio=authorized_optional_audio)
        checkpoint["phases"]["render"] = rendered
        if rendered["status"] == "rendered":
            checkpoint["phases"]["quality_control"] = quality_control(out / "video.mp4", script["duration_seconds"] + settings["meme_pause_seconds"])
    else:
        checkpoint["phases"]["render"] = {
            "status": "blocked",
            "code": "NEEDS_ASSETS",
            "reason": "No rights-cleared, scene-matched gameplay was supplied. Mobile storytelling does not fall back to vector graphics.",
            "style_profile": policy["production"].get("video_style", "yuzhen-mobile-storytelling"),
        }
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


def render_video(gameplay, voice, out, script, settings, *, authorized_optional_audio=()):
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
    include_sfx = sfx.exists() and "meme-sfx.wav" in authorized_optional_audio
    include_music = music.exists() and "music.wav" in authorized_optional_audio
    if include_sfx: inputs += ["-i", str(sfx)]
    if include_music: inputs += ["-i", str(music)]
    # Keep the source game capture intact apart from proportional crop/scale to the requested canvas.
    subtitle_path = str(srt).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    width, height = settings["target_width"], settings["target_height"]
    video_filter = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},subtitles='{subtitle_path}'"
    audio_parts = [f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,atrim=start=0:end={pause_at},asetpts=PTS-STARTPTS[before];anullsrc=channel_layout=stereo:sample_rate=48000:d={pause_duration}[gap];[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,atrim=start={pause_at},asetpts=PTS-STARTPTS[after];[before][gap][after]concat=n=3:v=0:a=1[voice]"]
    mix = "[voice]"
    next_input = 2
    if include_sfx:
        delay = round(pause_at * 1000)
        audio_parts.append(f"[{next_input}:a]adelay={delay}|{delay},volume=1[sfx]")
        mix = "[voice][sfx]"
        next_input += 1
    if include_music:
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
    return {"status": "rendered", "artifact": str(target.relative_to(ROOT)), "meme_pause_seconds": pause_duration, "sfx_included": include_sfx, "music_included": include_music}


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
    command = sub.add_parser("run", help="produce an entertainment checkpoint, check news, or preflight real footage")
    command.add_argument("--game", required=True)
    command.add_argument("--mode", choices=("ENTERTAINMENT", "NEWS", "REAL_FOOTAGE_FIRST"), default="ENTERTAINMENT")
    command.add_argument("--voice", help="existing voice WAV")
    command.add_argument("--storyboard", help="storyboard JSON for REAL_FOOTAGE_FIRST")
    command.add_argument("--candidates", help="candidate manifest JSON for REAL_FOOTAGE_FIRST")
    command.add_argument("--output-dir", help="separate real-footage output directory")
    command.add_argument("--output-mode", choices=("SAFE", "INTERNAL_REVIEW"), default="SAFE")
    args = parser.parse_args()
    sys.exit(run(args))


if __name__ == "__main__": main()

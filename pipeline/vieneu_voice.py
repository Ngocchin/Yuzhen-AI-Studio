"""Optional VieNeu-TTS v3 Turbo adapter; Piper remains a separate fallback."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "assets/models/vieneu-v3-turbo"
CODEC_DIR = ROOT / "assets/models/vieneu-moss-codec"
HF_CACHE = ROOT / "assets/models/vieneu-hf-cache"
VENV_PYTHON = ROOT / ".vieneu-venv/bin/python"
MODEL_REVISION = "61b85e3d937fbbacb387714180e8182823512523"
CODEC_REVISION = "ceff0d0749bfb3fa2d61149794ec6feef0d1e1ae"
SAMPLE_PARAGRAPHS = [
    ("Ủa alo? Tui mới về nhà farm thêm đúng một món thôi mà!", 0.22),
    ("Quay ra cái team bay màu sạch luôn rồi!", 0.18),
    ("Khoan... vậy ai đang thủ trụ?", 0.30),
    ("Trời ơi, cái trụ cuối cũng mất luôn!", 0.0),
]


def readiness() -> dict:
    config = MODEL_DIR / "onnx_update/config.json"
    required = [
        config,
        MODEL_DIR / "onnx_update/tokenizer.json",
        MODEL_DIR / "onnx_update/vieneu_prefill.onnx",
        MODEL_DIR / "onnx_update/vieneu_decode_step.onnx",
        MODEL_DIR / "onnx_update/vieneu_acoustic_cached.onnx",
        MODEL_DIR / "onnx_update/vieneu_backbone_shared.data",
        MODEL_DIR / "onnx_update/vieneu_v3_heads.npz",
        CODEC_DIR / "moss_audio_tokenizer_decode_full.onnx",
        CODEC_DIR / "moss_audio_tokenizer_decode_shared.data",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file() or path.stat().st_size == 0]
    return {
        "engine": "VieNeu-TTS v3 Turbo",
        "sdk_python": str(VENV_PYTHON),
        "sdk_installed": VENV_PYTHON.is_file(),
        "model_revision": MODEL_REVISION,
        "codec_revision": CODEC_REVISION,
        "model_available": not missing and VENV_PYTHON.is_file(),
        "missing": missing,
        "install_command": "bash scripts/setup_vieneu.sh",
    }


def _sdk_environment() -> dict[str, str]:
    env = os.environ.copy()
    env["HF_HOME"] = str(HF_CACHE)
    env["HF_HUB_DISABLE_TELEMETRY"] = "1"
    return env


def _load_engine():
    state = readiness()
    if not state["model_available"]:
        raise RuntimeError("VieNeu is not installed or its pinned CPU model is incomplete; run bash scripts/setup_vieneu.sh")
    if Path(sys.prefix).resolve() != VENV_PYTHON.parent.parent.resolve():
        # Re-enter with the isolated SDK environment; keep Piper's dependencies untouched.
        raise RuntimeError("Use .vieneu-venv/bin/python -m pipeline.vieneu_voice ... for VieNeu commands.")
    os.environ["HF_HOME"] = str(HF_CACHE)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    from vieneu import Vieneu

    return Vieneu(
        backbone_repo=str(MODEL_DIR),
        onnx_dir=str(MODEL_DIR / "onnx_update"),
        backend="onnx",
        precision="fp32",
        threads=2,
    )


def installed_voices() -> dict:
    try:
        tts = _load_engine()
    except Exception as error:
        return {"status": "blocked", "reason": str(error), "readiness": readiness()}
    voices = [{"label": label, "canonical_name": name} for label, name in tts.list_preset_voices()]
    return {"status": "ready", "sdk_version": __import__("importlib.metadata", fromlist=["version"]).version("vieneu"), "backend": tts.backend, "voices": voices}


def validate_wav(path: Path) -> dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return {"status": "blocked", "reason": "ffprobe is not installed."}
    result = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_name,sample_rate,channels", "-show_entries", "format=format_name,duration", "-of", "json", str(path)],
        capture_output=True,
        text=True,
    )
    try:
        data = json.loads(result.stdout)
        stream = data.get("streams", [])[0]
        duration = float(data.get("format", {}).get("duration", 0))
    except (ValueError, IndexError, json.JSONDecodeError):
        return {"status": "invalid", "reason": result.stderr.strip() or "No readable audio stream."}
    if result.returncode or duration <= 0 or path.stat().st_size <= 44:
        return {"status": "invalid", "reason": result.stderr.strip() or "Audio is empty or has no duration."}
    return {"status": "validated", "path": str(path), "bytes": path.stat().st_size, "duration_seconds": duration, "format": data.get("format", {}).get("format_name"), "audio": stream}


def _canonical_voice(tts, requested_name: str) -> str:
    if requested_name.strip().casefold() == "adam":
        raise ValueError("The Adam preset is excluded by the project voice policy.")
    available = tts.list_preset_voices()
    installed_names = {canonical for _, canonical in available}
    # Older locked SDK releases expose the exact preset name directly, while
    # newer releases may retain renamed presets through a resolver alias.
    resolved = requested_name if requested_name in installed_names else None
    resolver = getattr(tts, "resolve_voice_name", None)
    if not resolved and resolver:
        resolved = resolver(requested_name)
    if not resolved or resolved not in installed_names:
        raise ValueError(f"Voice {requested_name!r} is unavailable in this installed SDK roster.")
    return resolved


def _synthesize(tts, requested_name: str, output: Path, text: str | None = None) -> dict:
    if output.exists():
        return {"status": "refused", "reason": "Output exists; refusing to overwrite.", "path": str(output)}
    canonical = _canonical_voice(tts, requested_name)
    import numpy as np
    import soundfile as sf

    sample_rate = int(tts.sample_rate)
    if text is None:
        chunks = []
        for phrase, pause_seconds in SAMPLE_PARAGRAPHS:
            audio_chunk = np.asarray(tts.infer(phrase, voice=canonical), dtype=np.float32).reshape(-1)
            if not audio_chunk.size:
                raise RuntimeError(f"VieNeu returned an empty segment for {canonical}.")
            chunks.append(audio_chunk)
            if pause_seconds:
                chunks.append(np.zeros(round(sample_rate * pause_seconds), dtype=np.float32))
        audio = np.concatenate(chunks)
    else:
        audio = np.asarray(tts.infer(text, voice=canonical), dtype=np.float32).reshape(-1)
        if not audio.size:
            raise RuntimeError(f"VieNeu returned an empty segment for {canonical}.")
    output.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output), audio, sample_rate, subtype="PCM_16", format="WAV")
    check = validate_wav(output)
    if check["status"] != "validated":
        output.unlink(missing_ok=True)
        return {"status": "invalid", "validation": check}
    return {"status": "generated", "requested_voice": requested_name, "canonical_voice": canonical, "path": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "validation": check}


PREVIEW_SCRIPTS = {
    "A": {
        "label": "CASUAL STORYTELLING",
        "segments": [
            ("Tui nói thiệt nha, chơi Liên Quân đôi khi không sợ team địch mạnh.", 0.22),
            ("Chỉ sợ đồng đội mình tự tin quá thôi!", 0.0),
        ],
    },
    "B": {
        "label": "HYPE GAMING",
        "segments": [
            ("Ủa khoan khoan!", 0.15),
            ("Team mình đang combat kìa!", 0.18),
            ("Đợi tui một xíu...", 0.36),
            ("Trời ơi! Tui vừa tới nơi thì cả team bay màu hết rồi!", 0.0),
        ],
    },
    "C": {
        "label": "MEME REACTION",
        "segments": [
            ("Tui chỉ xin farm thêm đúng một món thôi mà...", 0.38),
            ("Ủa? Cái gì vậy?", 0.20),
            ("Sao nhà mình mất luôn rồi?", 0.18),
            ("Alo, ai giải thích giùm tui với!", 0.0),
        ],
    },
}


def _audio_metrics(path: Path) -> dict:
    import numpy as np
    import soundfile as sf

    samples, sample_rate = sf.read(str(path), dtype="float32", always_2d=True)
    peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    rms = float(np.sqrt(np.mean(np.square(samples)))) if samples.size else 0.0
    return {
        "sample_rate": sample_rate,
        "channels": int(samples.shape[1]) if samples.ndim > 1 else 1,
        "peak_dbfs": round(20 * np.log10(max(peak, 1e-12)), 2),
        "rms_dbfs": round(20 * np.log10(max(rms, 1e-12)), 2),
        "near_full_scale_samples": int(np.count_nonzero(np.abs(samples) >= 0.999)),
        "sample_count": int(samples.shape[0]),
    }


def create_min_quan_previews(output_dir: Path | None = None) -> dict:
    """Generate three text/prosody previews using the exact male Minh Quân preset."""
    try:
        tts = _load_engine()
    except Exception as error:
        return {"status": "blocked", "reason": str(error), "readiness": readiness()}

    roster = tts.list_preset_voices()
    if "Minh Quân" not in {voice_name for _, voice_name in roster}:
        return {
            "status": "blocked",
            "reason": "The installed SDK does not list the exact 'Minh Quân' preset. Refusing to substitute or relabel another voice.",
            "installed_voices": [{"label": label, "preset_id": name} for label, name in roster],
        }
    voice_detail = tts.get_preset_voice("Minh Quân")
    if str(voice_detail.get("gender", "")).casefold() not in ("male", "nam"):
        return {"status": "blocked", "reason": "The installed Minh Quân preset is not identified as male; refusing to synthesize."}

    if output_dir is None:
        output_dir = ROOT / "outputs/voice-previews/minh-quan"
    elif not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    if output_dir.exists():
        return {"status": "refused", "reason": "Preview directory already exists; refusing to overwrite.", "path": str(output_dir)}
    output_dir.mkdir(parents=True, exist_ok=False)

    import numpy as np
    import soundfile as sf

    sample_rate = int(tts.sample_rate)
    results = []
    for key, preview in PREVIEW_SCRIPTS.items():
        target = output_dir / f"preview-{key.lower()}.wav"
        pieces = []
        for segment, pause_seconds in preview["segments"]:
            generated = np.asarray(tts.infer(segment, voice="Minh Quân"), dtype=np.float32).reshape(-1)
            if not generated.size:
                raise RuntimeError(f"VieNeu returned an empty segment in Preview {key}.")
            pieces.append(generated)
            if pause_seconds:
                pieces.append(np.zeros(round(sample_rate * pause_seconds), dtype=np.float32))
        sf.write(str(target), np.concatenate(pieces), sample_rate, subtype="PCM_16", format="WAV")
        validation = validate_wav(target)
        if validation["status"] != "validated":
            target.unlink(missing_ok=True)
            results.append({"status": "invalid", "preview": key, "validation": validation})
            break
        results.append({
            "status": "generated",
            "preview": key,
            "label": preview["label"],
            "preset_id": "Minh Quân",
            "text": " ".join(segment for segment, _ in preview["segments"]),
            "path": str(target),
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "validation": validation,
            "signal_metrics": _audio_metrics(target),
        })

    report = {
        "status": "TECHNICAL_CHECKS_COMPLETE_HUMAN_REVIEW_REQUIRED" if len(results) == 3 and all(item["status"] == "generated" for item in results) else "BLOCKED_OR_PARTIAL",
        "engine": "VieNeu-TTS v3 Turbo",
        "sdk_version": __import__("importlib.metadata", fromlist=["version"]).version("vieneu"),
        "backend": tts.backend,
        "preset_id": "Minh Quân",
        "voice_metadata": {"gender": voice_detail.get("gender"), "description": voice_detail.get("description")},
        "style_control": "The SDK's style parameter is deprecated/ignored. Differences are prompted only by the supplied punctuation, sentence boundaries, and pauses; no forced speed, pitch shift, or SFX is applied.",
        "human_review_required": ["Vietnamese tone/diacritic pronunciation", "No words cut off", "Gaming terminology intelligibility", "Natural pacing and mode distinction", "Timbre and emotional naturalness", "No audible distortion or abnormal loudness"],
        "results": results,
    }
    (output_dir / "quality-review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": report["status"], **report, "output_dir": str(output_dir)}


def create_comparisons(output_dir: Path | None = None) -> dict:
    try:
        tts = _load_engine()
    except Exception as error:
        return {"status": "blocked", "reason": str(error), "readiness": readiness()}
    if output_dir is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        output_dir = ROOT / "outputs/voice-comparisons" / f"vieneu-v3-turbo-{stamp}"
    elif not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    if output_dir.exists():
        return {"status": "refused", "reason": "Comparison directory already exists; refusing to overwrite.", "path": str(output_dir)}
    output_dir.mkdir(parents=True, exist_ok=False)
    results = []
    filenames = ["minh-quan.wav", "anh-khoi.wav", "duc-tri.wav"]
    requested_names = ["Minh Quân", "Anh Khôi", "Đức Trí"]
    for requested, filename in zip(requested_names, filenames):
        result = _synthesize(tts, requested, output_dir / filename)
        results.append(result)
        if result["status"] != "generated":
            break
    manifest = {
        "engine": "VieNeu-TTS v3 Turbo",
        "sdk_version": __import__("importlib.metadata", fromlist=["version"]).version("vieneu"),
        "backend": tts.backend,
        "model_revision": MODEL_REVISION,
        "codec_revision": CODEC_REVISION,
        "text": "Ủa alo? Tui mới về nhà farm thêm đúng một món thôi mà! Quay ra cái team bay màu sạch luôn rồi! Khoan... vậy ai đang thủ trụ? Trời ơi, cái trụ cuối cũng mất luôn!",
        "prosody": "Four conversational clauses with brief context pauses; no pitch shift or post-processing beyond joining generated speech and pauses.",
        "human_listening_review_required": True,
        "results": results,
    }
    (output_dir / "comparison.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "generated" if len(results) == 3 and all(r["status"] == "generated" for r in results) else "partial", **manifest, "output_dir": str(output_dir)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="VieNeu-TTS v3 Turbo CPU voice adapter")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check")
    commands.add_parser("voices")
    sample = commands.add_parser("compare")
    sample.add_argument("--output-dir")
    preview = commands.add_parser("previews")
    preview.add_argument("--output-dir")
    synth = commands.add_parser("synthesize")
    synth.add_argument("--text", required=True)
    synth.add_argument("--voice", required=True)
    synth.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if args.command == "check":
        result = readiness()
    elif args.command == "voices":
        result = installed_voices()
    elif args.command == "compare":
        result = create_comparisons(Path(args.output_dir) if args.output_dir else None)
    elif args.command == "previews":
        result = create_min_quan_previews(Path(args.output_dir) if args.output_dir else None)
    else:
        try:
            tts = _load_engine()
            output = Path(args.output).expanduser()
            if not output.is_absolute():
                output = ROOT / output
            result = _synthesize(tts, args.voice, output, text=args.text)
        except Exception as error:
            result = {"status": "failed", "reason": str(error)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    successful_statuses = ("ready", "generated", "TECHNICAL_CHECKS_COMPLETE_HUMAN_REVIEW_REQUIRED")
    return 0 if result.get("status") in successful_statuses or result.get("model_available") else 1


if __name__ == "__main__":
    raise SystemExit(main())

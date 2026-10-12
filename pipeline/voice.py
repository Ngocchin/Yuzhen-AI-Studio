"""Piper voice discovery, manual model import, synthesis, and WAV validation."""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "assets/models/vi_VN-vais1000-medium.onnx"


def load_local_env():
    """Read simple KEY=VALUE settings without overriding the caller's environment."""
    env_file = ROOT / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_local_env()


def resolve_model(value=None):
    path = Path(value or os.environ.get("PIPER_MODEL", DEFAULT_MODEL)).expanduser()
    return path if path.is_absolute() else ROOT / path


def inspect(model=None, executable=None):
    model_path = resolve_model(model)
    config_path = Path(str(model_path) + ".json")
    piper = shutil.which(executable or os.environ.get("PIPER_BIN", "piper"))
    return {
        "engine": {"available": bool(piper), "path": piper},
        "model": {"path": str(model_path), "available": model_path.is_file(), "config_path": str(config_path), "config_available": config_path.is_file()},
        "ready": bool(piper and model_path.is_file() and config_path.is_file()),
        "license_note": "Confirm the exact voice model license and permitted use from its publisher before production. No license is inferred by this check."
    }


def validate_wav(path):
    path = Path(path).expanduser()
    ffprobe = shutil.which("ffprobe")
    if not path.is_file():
        return {"status": "invalid", "reason": f"File not found: {path}"}
    if not ffprobe:
        return {"status": "blocked", "reason": "ffprobe not installed; cannot validate WAV."}
    result = subprocess.run([ffprobe, "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_name,sample_rate,channels", "-show_entries", "format=format_name,duration", "-of", "json", str(path)], capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        duration = float(data.get("format", {}).get("duration", 0))
    except (json.JSONDecodeError, ValueError):
        streams, duration = [], 0
    if result.returncode or not streams or duration <= 0:
        return {"status": "invalid", "reason": result.stderr.strip() or "No readable audio stream or duration."}
    return {"status": "validated", "path": str(path), "format": data.get("format", {}).get("format_name"), "duration_seconds": duration, "audio": streams[0]}


def synthesize(text, output, model=None, executable=None):
    if not text.strip():
        return {"status": "invalid", "reason": "Text must not be empty."}
    readiness = inspect(model, executable)
    if not readiness["ready"]:
        return {"status": "blocked", "reason": "Piper is not ready. Install Piper and provide its Vietnamese ONNX model and matching .onnx.json file.", "readiness": readiness}
    piper = readiness["engine"]["path"]
    target = Path(output).expanduser()
    if not target.is_absolute():
        target = ROOT / target
    target.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([piper, "--model", readiness["model"]["path"], "--output_file", str(target)], input=text.encode("utf-8"), capture_output=True)
    if result.returncode:
        return {"status": "failed", "reason": result.stderr.decode(errors="replace")[-1500:]}
    validation = validate_wav(target)
    return {"status": "generated" if validation["status"] == "validated" else "invalid", "validation": validation}


def import_model(model_file, config_file, license_file, source):
    """Import user-downloaded artifacts; never fetch or infer their license."""
    model_file, config_file, license_file = map(lambda x: Path(x).expanduser(), (model_file, config_file, license_file))
    missing = [str(p) for p in (model_file, config_file, license_file) if not p.is_file()]
    if missing:
        return {"status": "invalid", "missing": missing}
    if model_file.stat().st_size == 0 or license_file.stat().st_size == 0:
        return {"status": "invalid", "reason": "Model and license files must not be empty."}
    try:
        json.loads(config_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"status": "invalid", "reason": "Piper model configuration must be valid JSON."}
    if not source.strip():
        return {"status": "invalid", "reason": "Provide the model publisher/source URL or exact source reference for your own records."}
    destination = ROOT / "assets/models"
    destination.mkdir(parents=True, exist_ok=True)
    model_target = destination / "vi_VN-vais1000-medium.onnx"
    config_target = Path(str(model_target) + ".json")
    license_target = destination / "MODEL-LICENSE.txt"
    shutil.copy2(model_file, model_target)
    shutil.copy2(config_file, config_target)
    license_target.write_text(f"Model: vi_VN-vais1000-medium\nSource: {source.strip()}\n\n" + license_file.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
    return {"status": "imported", "model": str(model_target), "config": str(config_target), "license_record": str(license_target), "git_ignored": True}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline Piper voice tools")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="inspect Piper executable and local voice files")
    check.add_argument("--model")
    check.add_argument("--executable")
    synth = commands.add_parser("synthesize", help="create and ffprobe-validate a real WAV")
    synth.add_argument("--text", required=True)
    synth.add_argument("--output", required=True)
    synth.add_argument("--model")
    synth.add_argument("--executable")
    validate = commands.add_parser("validate", help="validate an imported WAV with ffprobe")
    validate.add_argument("path")
    imp = commands.add_parser("import-model", help="copy manually obtained ONNX/config/license files into ignored local storage")
    imp.add_argument("--model-file", required=True)
    imp.add_argument("--config-file", required=True)
    imp.add_argument("--license-file", required=True)
    imp.add_argument("--source", required=True)
    args = parser.parse_args(argv)
    if args.command == "check": result = inspect(args.model, args.executable)
    elif args.command == "synthesize": result = synthesize(args.text, args.output, args.model, args.executable)
    elif args.command == "validate": result = validate_wav(args.path)
    else: result = import_model(args.model_file, args.config_file, args.license_file, args.source)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("ready") or result.get("status") in ("validated", "generated", "imported") else 1)


if __name__ == "__main__":
    main()

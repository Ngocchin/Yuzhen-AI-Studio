"""Select the configured speech engine while preserving Piper as the default."""
import json
import os
import subprocess
from pathlib import Path

from pipeline import vieneu_voice
from pipeline.voice import inspect as inspect_piper, synthesize as synthesize_piper

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/voice.json"


def load_config() -> dict:
    if not CONFIG.is_file():
        return {"active_engine": "piper", "selected_vieneu_voice": None}
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def inspect() -> dict:
    config = load_config()
    engine = config.get("active_engine", "piper")
    if engine == "piper":
        result = inspect_piper()
        result["active_engine"] = "piper"
        return result
    if engine == "vieneu":
        result = vieneu_voice.readiness()
        result["active_engine"] = "vieneu"
        result["selected_voice"] = config.get("selected_vieneu_voice")
        result["ready"] = bool(result.get("model_available") and result["selected_voice"])
        if result.get("model_available") and not result["selected_voice"]:
            result["reason"] = "Set selected_vieneu_voice in config/voice.json after listening to the comparison samples."
        return result
    return {"ready": False, "active_engine": engine, "reason": f"Unknown configured voice engine: {engine}"}


def synthesize(text: str, output: str | Path) -> dict:
    config = load_config()
    engine = config.get("active_engine", "piper")
    if engine == "piper":
        return synthesize_piper(text, output)
    if engine != "vieneu":
        return {"status": "blocked", "reason": f"Unknown configured voice engine: {engine}"}
    voice_name = config.get("selected_vieneu_voice")
    if not voice_name:
        return {"status": "blocked", "reason": "No VieNeu preset selected; listen to the comparison samples and set selected_vieneu_voice in config/voice.json."}
    if not vieneu_voice.VENV_PYTHON.is_file():
        return {"status": "blocked", "reason": "VieNeu SDK is not installed. Run bash scripts/setup_vieneu.sh."}
    target = Path(output).expanduser()
    if not target.is_absolute():
        target = ROOT / target
    command = [str(vieneu_voice.VENV_PYTHON), "-m", "pipeline.vieneu_voice", "synthesize", "--text", text, "--voice", str(voice_name), "--output", str(target)]
    env = os.environ.copy()
    env["HF_HOME"] = str(vieneu_voice.HF_CACHE)
    env["HF_HUB_OFFLINE"] = "1"
    env["HF_HUB_DISABLE_TELEMETRY"] = "1"
    try:
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
        data = json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        return {"status": "failed", "reason": str(error)}
    if result.returncode and data.get("status") not in ("generated",):
        data.setdefault("stderr", result.stderr[-1500:])
    return data

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
VENV="$ROOT/.vieneu-venv"
export HF_HOME="$ROOT/assets/models/vieneu-hf-cache"
export HF_HUB_DISABLE_TELEMETRY=1

if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install --disable-pip-version-check -r requirements-vieneu.txt

# Pin both public repositories so future Cloud tasks get the same artifacts.
"$VENV/bin/python" - <<'PY'
from pathlib import Path
import hashlib
import shutil
from huggingface_hub import snapshot_download, hf_hub_download

root = Path.cwd()
snapshot_download(
    repo_id="pnnbao-ump/VieNeu-TTS-v3-Turbo",
    revision="61b85e3d937fbbacb387714180e8182823512523",
    allow_patterns=["onnx_update/*", "voices_v3_turbo.json", "README.md"],
    local_dir=root / "assets/models/vieneu-v3-turbo",
)
snapshot_download(
    repo_id="OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX",
    revision="ceff0d0749bfb3fa2d61149794ec6feef0d1e1ae",
    allow_patterns=["*"],
    local_dir=root / "assets/models/vieneu-moss-codec",
)

checksums = {
    "assets/models/vieneu-v3-turbo/onnx_update/vieneu_prefill.onnx": "27f8b064f6b57b5448e95d095f1959588c005d614678045c2b97ecccf3b7a0f7",
    "assets/models/vieneu-v3-turbo/onnx_update/vieneu_decode_step.onnx": "bedc379cea61ea5d616312750d95ad3924e055856662d19187a889a5edc24ceb",
    "assets/models/vieneu-v3-turbo/onnx_update/vieneu_acoustic_cached.onnx": "f631e3387c788c3d8b9a5ac5df94952af5bc4c4d1049ff8a751e76a246fff2d4",
    "assets/models/vieneu-v3-turbo/onnx_update/vieneu_backbone_shared.data": "c7c072193db33d0542457e2612c7272c44c4279d1cafaf0aa4c379964911db2f",
    "assets/models/vieneu-v3-turbo/onnx_update/vieneu_v3_heads.npz": "fb22484baa424bbb775133a6e5f0d00d6299b2b256fbe3312a864b85b9aed01e",
    "assets/models/vieneu-moss-codec/moss_audio_tokenizer_decode_full.onnx": "0fbbafe3fd4afa2a019af5c5ced204af6e2d1db044fa40f021525d2aee95b4ac",
    "assets/models/vieneu-moss-codec/moss_audio_tokenizer_decode_shared.data": "e69d52e0f4e84ca27850557ee54face46632d3a5a16c89bd246c7c408466dcad",
    "assets/models/vieneu-moss-codec/moss_audio_tokenizer_decode_step.onnx": "9527c86a29e1837edec1f74db57d5eeaadb3a715af3382703566460afed25855",
}
for relative, expected in checksums.items():
    path = root / relative
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f"SHA-256 mismatch for {relative}: expected {expected}, got {actual}")

# VieNeu SDK 3.8.3 resolves the codec bundle through the HF cache and currently
# doesn't forward its engine's codec_dir option. ONNX Runtime requires its
# external .data file to be adjacent to the graph, so materialize those cache
# links in the pinned snapshot directory for its two decoder graphs.
repo = "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX"
for filename in ("moss_audio_tokenizer_decode_full.onnx", "moss_audio_tokenizer_decode_shared.data", "moss_audio_tokenizer_decode_step.onnx"):
    path = Path(hf_hub_download(repo, filename))
    if path.is_symlink():
        source = path.resolve(strict=True)
        path.unlink()
        shutil.copy2(source, path)

print("VieNeu-TTS 3.8.3 CPU assets installed and pinned under assets/models/ (Git-ignored).")
PY

printf 'Setup complete. Check voices with: %s -m pipeline.vieneu_voice voices\n' "$VENV/bin/python"

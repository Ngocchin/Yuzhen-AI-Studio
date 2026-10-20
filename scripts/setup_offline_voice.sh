#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_DIR="$ROOT_DIR/assets/models"
VENV_DIR="$ROOT_DIR/.venv"
REPO="https://huggingface.co/rhasspy/piper-voices"
REVISION="c10ece1aade47bb51c153c893d14e5bf8e5b7117"
VOICE_DIR="vi/vi_VN/vais1000/medium"
ONNX_NAME="vi_VN-vais1000-medium.onnx"
CONFIG_NAME="$ONNX_NAME.json"
ONNX_SHA256="ec7c89e2c85f4d1edc24b6120c18aaf1bda614f06b511567eb9c7c0de15e2dab"
CONFIG_GIT_BLOB="b11c938b28c4425d9be76beeb09d68f0d67157ba"
MODEL_CARD_GIT_BLOB="d77035517b7e2e9446d43b2c83769890e14b000c"

for tool in python3 curl sha256sum git; do
  command -v "$tool" >/dev/null || { echo "Missing required tool: $tool" >&2; exit 1; }
done

mkdir -p "$MODEL_DIR" "$ROOT_DIR/.cache/pip"
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  python3 -m venv "$VENV_DIR"
fi
PIP_CACHE_DIR="$ROOT_DIR/.cache/pip" "$VENV_DIR/bin/python" -m pip install -r "$ROOT_DIR/requirements-voice.txt"

download_if_needed() {
  local name="$1" expected_kind="$2" expected="$3" destination="$MODEL_DIR/$1"
  local actual tmp="$destination.part"
  if [[ "$expected_kind" == "sha256" && -f "$destination" ]]; then
    actual="$(sha256sum "$destination" | cut -d' ' -f1)"
  elif [[ "$expected_kind" == "gitblob" && -f "$destination" ]]; then
    actual="$(git -C "$ROOT_DIR" hash-object "$destination")"
  else
    actual=""
  fi
  if [[ "$actual" != "$expected" ]]; then
    rm -f "$tmp"
    curl --proto '=https' --tlsv1.2 -fLsS --retry 3 --max-time 300 \
      "$REPO/resolve/$REVISION/$VOICE_DIR/$name" -o "$tmp"
    if [[ "$expected_kind" == "sha256" ]]; then
      actual="$(sha256sum "$tmp" | cut -d' ' -f1)"
    else
      actual="$(git -C "$ROOT_DIR" hash-object "$tmp")"
    fi
    if [[ "$actual" != "$expected" ]]; then
      rm -f "$tmp"
      echo "Checksum mismatch for $name: expected $expected, got $actual" >&2
      exit 1
    fi
    mv "$tmp" "$destination"
  fi
}

download_if_needed "$ONNX_NAME" sha256 "$ONNX_SHA256"
download_if_needed "$CONFIG_NAME" gitblob "$CONFIG_GIT_BLOB"
download_if_needed "MODEL_CARD" gitblob "$MODEL_CARD_GIT_BLOB"

if [[ ! -f "$MODEL_DIR/MODEL-LICENSE.txt" ]]; then
  cat > "$MODEL_DIR/MODEL-LICENSE.txt" <<'LICENSE'
Piper model: vi_VN-vais1000-medium
Source repository: https://huggingface.co/rhasspy/piper-voices
Pinned repository revision: c10ece1aade47bb51c153c893d14e5bf8e5b7117
Model card: assets/models/MODEL_CARD
The repository metadata declares MIT. The model card identifies the VAIS-1000
Vietnamese Speech Synthesis Corpus and its CC BY 4.0 dataset license. Preserve
the model card and cite the corpus source when redistributing/using this voice:
VAIS-1000: A Vietnamese Speech Synthesis Corpus, submitted by Truong Do,
IEEE DataPort, DOI 10.21227/H2B887,
https://ieee-dataport.org/documents/vais-1000-vietnamese-speech-synthesis-corpus
Dataset license: https://creativecommons.org/licenses/by/4.0/

Piper engine package piper-tts 1.8.0 is GPL-3.0-or-later; see its package
metadata and upstream source for engine distribution obligations.
LICENSE
fi

echo "Piper environment and pinned Vietnamese voice files are ready."
echo "Run: python3 -m pipeline.voice check"

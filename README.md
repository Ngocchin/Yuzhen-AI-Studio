# Yuzhen-AI-Studio

Local-first production pipeline for TikTok and YouTube Shorts for **Yuzhen Chơi Gì**. Entertainment Mode works offline for ideation, scripts, storyboards, captions, and checkpoints. News Mode is blocked until verifiable source records are supplied. No content is published automatically.

## Quick start

```sh
python3 -m pipeline run --game "Liên Quân Mobile" --mode ENTERTAINMENT
```

The first run creates `outputs/lien-quan-mobile/` with three ideas, a 35–50 second script, timed storyboard, channel copy, and `checkpoint.json`. It attempts voice generation only if Piper and the Vietnamese model are installed. Rendering requires licensed gameplay at `assets/user/gameplay.mp4` and a validated narration WAV; absent inputs are listed in the checkpoint. It does not fabricate either.

## Offline Vietnamese voice

Install Piper using its official distribution for your platform and obtain the `vi_VN-vais1000-medium` ONNX model and matching JSON configuration from a source whose license permits your intended use. Place them at the paths in `.env.example`, or set `PIPER_MODEL`. Model downloads are not attempted automatically. Alternatively pass an existing voice WAV with `--voice path/to/voice.wav` (convert MP3 with ffmpeg first). WAV validation uses ffprobe.

## Media and modes

Supply only gameplay, reaction images, music, and SFX for which you have appropriate rights. Output target is 1080x1920 H.264/AAC MP4 with burned-in Vietnamese subtitles. At the marked meme beat, narration pauses for 0.65 seconds for SFX. NEWS mode stops with `NETWORK_BLOCKED` unless verifiable source URL, publisher, and publication date records are supplied. Each run saves phase artifacts and a resumable checkpoint under `outputs/<game-slug>/`.

Automated QC checks file metadata and audio/video stream presence; human listening and viewing remain necessary to judge voice quality, rights, subtitle readability, black frames, and creative quality. Agent role definitions are in `agents/`; executable role mapping is in `config/agents.json`, and defaults are in `config/defaults.json`. The Director runs sequentially with checkpoints; this runtime does not claim live subagent execution. Run all local checks with `python3 -m unittest discover -s tests`.

## Director and agents

Agent 00 coordinates agents 01–07 through checkpointed phases. Entertainment mode runs idea selection, script/storyboard, voice, rendering, QC, and channel copy in order. NEWS mode intentionally stops at the Trend Hunter evidence gate with `NETWORK_BLOCKED` when research sources cannot be independently verified. The files in `agents/` contain each role's operating rules; `config/agents.json` is the machine-readable registry. Channel copy generation never publishes.

## Piper voice setup

The voice adapter is `pipeline/voice.py`. It supports runtime discovery, WAV validation, synthesis, and manual model import. Run `bash scripts/setup_offline_voice.sh` to install the pinned Linux/Python dependencies into the ignored project `.venv`, download the pinned Vietnamese model files, and verify their digests. Model weights, package caches, the virtual environment, license record, and generated WAVs remain outside Git.

1. Run the setup script above. It installs Piper TTS 1.8.0 (GPL-3.0-or-later) and its pinned Linux/Python dependencies.
2. The script downloads `vi_VN-vais1000-medium.onnx`, its `.onnx.json`, and `MODEL_CARD` from the pinned `rhasspy/piper-voices` Hugging Face revision. It verifies the model SHA-256 and config/card Git blob hashes before accepting them.
3. The Hugging Face repo metadata declares MIT. The model card identifies the VAIS-1000 Vietnamese Speech Synthesis Corpus, with CC BY 4.0, and the IEEE DataPort record identifies the submitter as Truong Do, DOI `10.21227/H2B887`. Preserve `assets/models/MODEL_CARD` and `MODEL-LICENSE.txt`; include attribution to VAIS-1000 and its source when required. Review the full license terms for your intended commercial and redistribution use. Piper engine licensing does not replace voice/data attribution.
4. To import another copy manually, provide its ONNX file, matching `.onnx.json`, license text, and source reference:

   ```sh
   python3 -m pipeline.voice import-model \
     --model-file /path/to/vi_VN-vais1000-medium.onnx \
     --config-file /path/to/vi_VN-vais1000-medium.onnx.json \
     --license-file /path/to/model-license.txt \
     --source 'publisher URL or exact source reference'
   ```

5. Check readiness, then synthesize and validate a real WAV:

   ```sh
   python3 -m pipeline.voice check
   python3 -m pipeline.voice synthesize --text 'Xin chào, đây là giọng đọc thử tiếng Việt.' --output outputs/voice-check.wav
   python3 -m pipeline.voice validate outputs/voice-check.wav
   ```

The adapter automatically discovers `.venv/bin/piper` and the default model in `assets/models/`. Set `PIPER_BIN` and `PIPER_MODEL` in the untracked local `.env` file only if your installation uses other paths; `.env.example` shows the keys. Synthesis is successful only when Piper exits successfully and ffprobe confirms a non-empty WAV audio stream.

### Reuse in Codex Cloud

For a fresh Cloud environment, add this one-line setup command in the selected environment's **Setup script** field after this repository branch is available there:

```sh
cd /workspace/Yuzhen-AI-Studio && bash scripts/setup_offline_voice.sh
```

The script is safe to rerun: it reuses an existing `.venv` and model after checksum verification, and repairs missing/corrupt files. Current Cloud configuration can be changed from the Codex Cloud Environments settings UI; this task cannot write that UI setting. The setup command needs outbound access to PyPI and Hugging Face through the configured proxy.

## Continue the first production

Provide rights-cleared gameplay at `assets/user/gameplay.mp4`, plus a verified voice WAV or a working Piper installation/model. Optional `assets/user/meme-sfx.wav` and `assets/user/music.wav` are mixed if present. Then resume with:

```sh
python3 -m pipeline run --game "Liên Quân Mobile" --mode ENTERTAINMENT
```

For a manually supplied voice WAV, add `--voice /absolute/path/to/voice.wav`. Models, WAVs, MP3s, MP4s, and `.env` are ignored by Git. No credentials, model weights, or generated video should be committed.

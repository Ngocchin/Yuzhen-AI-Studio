# Third-party voice engine notices

VieNeu-TTS SDK and VieNeu-TTS-v3-Turbo model artifacts are distributed under Apache License 2.0 according to their publishers. The separate MOSS Audio Tokenizer Nano ONNX codec repository also declares Apache-2.0.

- SDK/source: [pnnbao97/VieNeu-TTS](https://github.com/pnnbao97/VieNeu-TTS), author Phạm Nguyễn Ngọc Bảo.
- Model, presets, and model card: [pnnbao-ump/VieNeu-TTS-v3-Turbo](https://huggingface.co/pnnbao-ump/VieNeu-TTS-v3-Turbo), revision `61b85e3d937fbbacb387714180e8182823512523`.
- Codec: [OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX](https://huggingface.co/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX), revision `ceff0d0749bfb3fa2d61149794ec6feef0d1e1ae`.

The setup script checks downloaded large files against the Hugging Face LFS SHA-256 values. Representative verified digests include the main shared ONNX weights `c7c072193db33d0542457e2612c7272c44c4279d1cafaf0aa4c379964911db2f` and codec decoder data `e69d52e0f4e84ca27850557ee54face46632d3a5a16c89bd246c7c408466dcad`; the remaining active graph/hash list is in `scripts/setup_vieneu.sh`.

The model card states that the shipped preset voice assets and generated audio may be used commercially under Apache-2.0. Keep the project/model attribution and Apache license notice when redistributing model files. The model card also credits MOSS-Audio-Tokenizer-Nano and sea-g2p; see each upstream repository for its notices. Model weights, ONNX files, and generated comparison audio are not committed to this repository.

# TG Media Manager Model Management Architecture

## Status

Accepted. This is the permanent architecture record for model delivery and runtime cache management.

## Goals

- Keep Docker images small and portable.
- Store model weights outside the image in the persistent `/models` volume.
- Let the Web UI configure and download models after deployment.
- Support official model sources, user-trained model artifacts, and future model-pack manifests.
- Preserve privacy: models are downloaded locally by the NAS/container, and media is not uploaded.

## Model Sources

TG Media Manager supports three source types.

### Official Sources

Use the upstream model/library download flow when it is reliable.

Examples:

- OpenCLIP models are cached through `open_clip`.
- InsightFace `buffalo_l` is cached through InsightFace.
- faster-whisper models are cached through `faster-whisper`.
- SenseVoice GGUF is a direct official Hugging Face artifact:
  `https://huggingface.co/FunAudioLLM/SenseVoiceSmall-GGUF/resolve/main/sensevoice-small.gguf`

Official sources are preferred for common models because they are easier to verify and update. When a verified direct artifact exists, the registry can provide it as a built-in default so the Web UI can download it without manual URL entry.

### Direct Artifact URLs

Use direct URLs for deploy-friendly model files:

- `.gguf`
- `.onnx`
- `.pt`
- `.bin`
- `.zip`
- `.tar.zst`

Good hosts:

- GitHub Release assets
- Hugging Face file URLs
- Cloudflare R2 / S3-compatible object storage
- A private static file server

The Web UI stores these URLs in the local SQLite settings table, then download jobs place files under `/models`.

### Model-Pack Manifest

Future model packs should use a JSON manifest:

```json
{
  "name": "BSakura TGMM Model Pack",
  "version": "1.0.0",
  "models": [
    {
      "id": "sensevoice-small-gguf",
      "url": "https://github.com/BSakura-Miku/tgmm-models/releases/download/v1.0.0/SenseVoiceSmall.gguf",
      "sha256": "sha256-here",
      "path": "/models/sensevoice/SenseVoiceSmall.gguf"
    }
  ]
}
```

The manifest approach is the recommended long-term path for user-trained models because it provides versioning, checksums, and repeatable NAS migration.

## Runtime Paths

The container sets cache paths into `/models`:

- `MODEL_ROOT=/models`
- `HF_HOME=/models/huggingface`
- `TORCH_HOME=/models/torch`
- `XDG_CACHE_HOME=/models/cache`
- `INSIGHTFACE_HOME=/models/insightface`

Model downloads must never write into the image layer as the primary cache.

## Versioning

Downloaded model files and cache markers are tracked by TGMM metadata under:

```text
/models/.tgmm-models/
```

Runtime-cache models may share upstream cache directories, so deleting them from the UI only removes the TGMM readiness marker unless the model owns a dedicated file/directory.

## Current Implementation

- `/api/models` lists model status, configured source URL, official reference URL, size, path, and cache state.
- `/api/models/source` saves per-model direct URLs and optional SHA256.
- Web model cards can save source URLs and trigger download jobs.
- Download jobs use Web settings first, then environment variables, then registry defaults.

## Future Work

- Parse model-pack manifests and list installable model versions.
- Verify and extract `.zip` / `.tar.zst` packs into declared paths.
- Support authenticated private GitHub/Hugging Face downloads using a local secret.
- Add local upload for model files from the Web UI.
- Record model provenance in `/models/model_index.json`.

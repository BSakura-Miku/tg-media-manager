# TG Media Manager

Local Dockerized manager for a Telegram-downloaded media library.

## Quick Start

```bash
docker compose up --build
```

Open:

```text
http://localhost:8787
```

Default media mount in `docker-compose.yml`:

```text
/tmp/bssecondary_mount/BS-Media2/BS-Lsp/Tgdownloads/LSP:/media
```

## Safety

- The dashboard and summary endpoints are read-only.
- Jobs that move files must be started explicitly.
- All moves are logged through the existing `_MANIFESTS/applied_moves.csv` workflow.
- Face and image model support is designed for local-only inference; no uploads are performed.
- Web Settings are stored in `/data/tg_media_manager.sqlite3`, not baked into the Docker image.
- NAS deployments require `APP_PASSWORD` and an independent random `APP_SECRET` in the local Compose `.env` file.
- Authentication uses a signed, expiring, HTTP-only session cookie. Model downloads reject private-network targets, redirects to unsafe targets, unbounded payloads, and unverified custom sources by default.
- `.env`, databases, media, models, embeddings, thumbnails, and transcripts must stay outside Git. The repository contains variable names and examples only, never deployment secrets.

## Web Features

- Dark and light themes.
- English and Simplified Chinese UI.
- Settings page for container media source root, organized library root, and source subdirectories.
- Face Groups card view with local cached thumbnails and manual group naming.
- Search across manifests, move plans, applied moves, filename analysis, and face groups.

Path settings use container paths. Add Docker volumes first, then select those mounted paths in the Web UI.

## Mac ARM and x86 NAS

Local Mac development can use the default ARM build. For an x86_64 NAS, build or push linux/amd64 images with Buildx:

```bash
make build-amd64
make push-base-amd64 DOCKERHUB_REPO=bsakuramiku/tg-media-manager
```

For the full local face-clustering image:

```bash
make push-vision-amd64 DOCKERHUB_REPO=bsakuramiku/tg-media-manager
```

If Docker Hub is unavailable, export a tar for transfer:

```bash
make save-amd64
make save-vision-amd64
```

When creating a small hotfix context from macOS, prefix manual `tar` commands with `COPYFILE_DISABLE=1` to avoid Apple extended-attribute headers in the NAS extraction log.

NAS compose is designed to live at:

```text
/volume1/docker/tg-media-manager/docker-compose.yaml
```

It follows the existing NAS style: project data is stored in relative `./data` and `./models`, while the media library is mounted from:

```text
/volume4/BS-Secondary/BS-Media2/BS-Lsp/Tgdownloads/LSP
```

Start on NAS:

```bash
cd /volume1/docker/tg-media-manager
cp .env.nas.example .env
# Replace both placeholder values before starting. Keep APP_SECRET different
# from APP_PASSWORD; `openssl rand -hex 32` is suitable for APP_SECRET.
docker compose up -d
```

The NAS image can also be transferred without Docker Hub:

```bash
docker buildx build --platform linux/amd64 \
  --build-arg APP_SEMVER=1.2.0 \
  -t tg-media-manager:nas-1.2.0-amd64 \
  -f docker/Dockerfile.clip --load .
docker save tg-media-manager:nas-1.2.0-amd64 -o /tmp/tg-media-manager-1.2.0.tar
```

Back up `./data/tg_media_manager.sqlite3` before changing the image. Schema upgrades are additive and idempotent, but a database backup remains the rollback boundary.

## Search And Indexing

- Filename, tags, authors, face groups, subtitles, and media metadata remain directly searchable.
- BGE text embeddings and OpenCLIP image embeddings provide local semantic ranking. If a model is absent, the API reports the fallback instead of labelling a hash vector as an AI embedding.
- Existing OpenCLIP JSONL caches and face-group CSV manifests are imported into SQLite, avoiding a full inference rerun after an upgrade.
- Full workflows repair missing thumbnails, preserve the earliest original filename, backfill hashes incrementally, and finish with a quality gate. Partial coverage is reported as `warning`, not a false success.
- Timed subtitles use Faster-Whisper when SenseVoice output lacks usable timestamps. Confirmed no-speech results are not repeatedly reprocessed.

Run the local quality gate before deployment:

```bash
make check
```

## Vision Builds

The base image does not install ML packages. For local-only face clustering:

```bash
docker compose -f docker-compose.yml -f docker-compose.vision.yml up --build
```

This installs InsightFace, ONNX Runtime, and OpenCV in the container, not on the host.

OpenCLIP image classification is intentionally separate because Torch wheels are large:

```bash
docker compose -f docker-compose.yml -f docker-compose.clip.yml up --build
```

## CLI Commands

```bash
python backend/core/tg_media_library.py --root /media --output-root /media scan
python backend/core/tg_media_library.py --root /media --output-root /media analyze-filenames
python backend/core/tg_media_library.py --root /media --output-root /media classify-keywords
python backend/core/tg_media_library.py --root /media --output-root /media refresh-state
python backend/core/tg_media_library.py --root /media --output-root /media extract-frames --limit 120
python backend/core/tg_media_library.py --root /media --output-root /media face-scan --limit 120
python backend/core/tg_media_library.py --root /media --output-root /media face-cluster
python backend/core/tg_media_library.py --root /media --output-root /media face-cluster-report
python backend/core/tg_media_library.py --root /media --output-root /media apply-face-groups
```

`apply-face-groups` is dry-run by default. Add `--apply` only after reviewing `_MANIFESTS/face_move_plan.csv`.

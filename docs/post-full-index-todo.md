# Post Full-Index TODO

Status: waiting for the current NAS full-library job to finish.

Recent fixes already shipped locally:

- v1.0.14: media library pagination, thumbnail cache revision `media_thumbs_v8`, first-screen thumbnail priority loading, author/face collection zoom consistency, job detail overflow guard.
- v1.0.15: proactive infinite loading for media library and random waterfall, so pages keep loading when the user gets near the bottom.
- v1.1.2-dev: batch thumbnail health diagnostics and `repair-thumbnails` workflow for missing/corrupted preview cache.

Do not restart or update the NAS container while the long-running index job is active. Use this file as the unified queue for fixes and optimizations to apply after the run completes.

## UI Fixes

- Face groups: remove the black translucent horizontal overlay from face-group thumbnails. Face cards should keep the image unobstructed and move metadata into compact chips or a separate lower area.
- Media cards: keep metadata readable without blocking the center of images or videos. Prefer small bottom chips and progressive hover/detail disclosure.
- Job detail panel: keep watching for new overflow cases after more NAS jobs finish; the current long command/path overflow is fixed in v1.0.14.
- Dashboard storage card: capacity plus count is implemented, for example `视频 300 GB（1,000 部）` and `图片 80 GB（6,000 张）`.

## Thumbnail And Preview Pipeline

- Investigate yellow/green/magenta corrupted thumbnails in the media library. Likely causes are stale/bad cached previews or hardware-decoded frame color-format artifacts now exposed because the Web UI reuses `frame_index.csv`.
- Done locally: add a thumbnail health checker that detects obvious corrupt previews: extreme green dominance, repeated horizontal bands, near-empty frames, invalid image decode, and suspicious dimensions.
- Done locally: for photos, prefer Pillow thumbnails from the original image instead of FFmpeg hardware decode.
- Done locally: for videos, repair corrupt cached previews with software FFmpeg decode and overwrite only the bad cached preview.
- Add per-media and batch `regenerate thumbnail/contact sheet` actions.
- Add cache invalidation for old bad previews in `_MANIFESTS/vision_cache`, `_MANIFESTS/media_thumbs_v*`, and `frame_index.csv`.
- Done locally: generate and serve small thumbnails for photos; only load original media when the viewer opens the item.

## Performance

- Precompute/cache the tag graph response; `/api/tags/graph` is still much slower than media and thumbnail endpoints.
- Keep using existing extracted frames for media thumbnails and contact sheets; avoid generating thumbnails during page load.
- Add thumbnail prewarm after frame extraction so media library and waterfall pages are fast on first open.
- Add a generated thumbnail health manifest so `/api/media/{id}/thumbnail` can avoid reopening cached JPEGs on every request.
- Make metadata indexing use chunked writes and heartbeat updates throughout every heavy stage.
- Consider parallelism for safe CPU-bound indexing steps while avoiding NAS disk I/O saturation.
- Add a Web performance panel showing API latency, thumbnail cache hits, model device, worker counts, and current job throughput.

## Full-Run Validation

- After the NAS job finishes, audit sample media for original filename preservation, generated thumbnails, vision tags, face groups, transcripts, subtitle files, and timeline rows.
- Check whether corrupted thumbnails are source-file corruption or generated-cache corruption before deleting any cache.
- Rebuild only affected caches first, then run a small UI validation pass before deploying a new image.

## v1.3 Audit Follow-ups

Completed in v1.3.0:

- Persisted PBKDF2 password credentials, current-password verification, login throttling, and session-version invalidation.
- Atomic job enqueue, terminal-job cancel rejection, merged stdout/stderr consumption, and cancel-file cleanup.
- Frame, vision, and face checkpoints now merge with prior full indexes and use atomic file replacement.
- Semantic and similarity rebuilds are scoped to the selected media root; unchanged semantic text vectors are reused.
- Natural-language parser fixes for photo/video ambiguity, negative favorite/subtitle filters, and duration direction.
- Full semantic candidate recall, minimum relevance threshold, strict intent preservation, and metadata-wide exclusions.
- Media-library refresh, job-detail terminal synchronization, login error feedback, modal focus restoration, and mobile action target sizing.
- Thumbnail invalidation when the source media is newer than the cached thumbnail.

Still planned after measuring v1.3.0 on the NAS:

- Move semantic vectors from Python full scans to sqlite-vec/HNSW once the library approaches 50k media.
- Split long subtitle text into timestamped BGE chunks and aggregate top chunks per media.
- Add a versioned input/model fingerprint to frame, face, vision, and thumbnail caches.
- Batch OpenCLIP inference; Intel iGPU acceleration requires an OpenVINO-exported vision encoder rather than PyTorch OpenCLIP.
- Persist transcription failure fingerprints, retry backoff, and atomic VTT/database commits.
- Replace the in-process monitor loop with a database lease if the service is ever run with multiple web workers.
- Add a fixed, privacy-safe semantic quality set and track Recall@10, Precision@10, MRR, and p95 latency.

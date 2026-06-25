# Post Full-Index TODO

Status: waiting for the current NAS full-library job to finish.

Do not restart or update the NAS container while the long-running index job is active. Use this file as the unified queue for fixes and optimizations to apply after the run completes.

## UI Fixes

- Face groups: remove the black translucent horizontal overlay from face-group thumbnails. Face cards should keep the image unobstructed and move metadata into compact chips or a separate lower area.
- Media cards: keep metadata readable without blocking the center of images or videos. Prefer small bottom chips and progressive hover/detail disclosure.
- Job detail panel: ensure long command, current path, heartbeat, and stdout lines wrap or scroll inside the card instead of overflowing to the right.
- Dashboard storage card: show capacity plus count, for example `视频 300 GB（1,000 部）` and `图片 80 GB（6,000 张）`.

## Thumbnail And Preview Pipeline

- Investigate yellow/green/magenta corrupted thumbnails in the media library. Likely causes are stale/bad cached previews or hardware-decoded frame color-format artifacts now exposed because the Web UI reuses `frame_index.csv`.
- Add a thumbnail health checker that detects obvious corrupt previews: extreme green dominance, repeated horizontal bands, near-empty frames, invalid image decode, and suspicious dimensions.
- For photos, prefer PIL/ImageMagick thumbnails from the original image instead of FFmpeg hardware decode.
- For videos, retry corrupt VAAPI-extracted frames with software decode and overwrite only the bad cached preview.
- Add per-media and batch `regenerate thumbnail/contact sheet` actions.
- Add cache invalidation for old bad previews in `_MANIFESTS/vision_cache`, `_MANIFESTS/media_thumbs_v*`, and `frame_index.csv`.
- Generate and serve small thumbnails for photos during indexing; only load original media when the viewer opens the item.

## Performance

- Precompute/cache the tag graph response; `/api/tags/graph` is still much slower than media and thumbnail endpoints.
- Keep using existing extracted frames for media thumbnails and contact sheets; avoid generating thumbnails during page load.
- Add thumbnail prewarm after frame extraction so media library and waterfall pages are fast on first open.
- Make metadata indexing use chunked writes and heartbeat updates throughout every heavy stage.
- Consider parallelism for safe CPU-bound indexing steps while avoiding NAS disk I/O saturation.
- Add a Web performance panel showing API latency, thumbnail cache hits, model device, worker counts, and current job throughput.

## Full-Run Validation

- After the NAS job finishes, audit sample media for original filename preservation, generated thumbnails, vision tags, face groups, transcripts, subtitle files, and timeline rows.
- Check whether corrupted thumbnails are source-file corruption or generated-cache corruption before deleting any cache.
- Rebuild only affected caches first, then run a small UI validation pass before deploying a new image.

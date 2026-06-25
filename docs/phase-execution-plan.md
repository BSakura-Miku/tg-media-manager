# TG Media Manager Five-Phase Execution Plan

Status: active.

This document is the durable execution record for the five product phases discussed during early development. It complements `PRODUCT_ROADMAP.md` by tracking what is implemented now, what still needs NAS full-library validation, and what must not be changed while a long-running NAS job is active.

## Operating Rule

- Do not restart or update the NAS container while a full-library job is running.
- Local code checks and documentation may continue.
- Real media validation waits until the NAS full-library job finishes.
- Every phase must be verifiable from code plus, later, the NAS SQLite database and `/media/_MANIFESTS` outputs.

## Phase 1: Product UX and Workflow Foundation

Goal: make the manager understandable and operable from the Web UI.

Implemented:

- Dashboard, jobs, media library, tag graph, random waterfall, models, authors, face groups, logs, and settings pages.
- Human-readable workflows such as full library, new downloads, review cleanup, face, vision, dedupe, transcription, and model downloads.
- Job grouping by running, failed, completed, and other states.
- Job detail progress with stage and workflow-step context.
- Dark/light theme, bilingual UI, version display, and redesigned app shell.
- Media viewer with playback, details, tags, favorite, safe-delete, manual tag, and manual author editing.
- Dashboard storage card with capacity plus count per media type; Simplified Chinese uses `部` for videos and `张` for photos.

Validation after NAS full run:

- Open every navigation page and at least one child/detail view.
- Confirm long paths and job details do not overflow on desktop or mobile width.
- Confirm recent media, random waterfall, authors, faces, and logs update from the current database.
- Confirm dashboard storage shows examples like `视频 300 GB（1,000 部）` and `图片 80 GB（6,000 张）`, with the ring chart based on bytes.

## Phase 2: Metadata Database and Virtual Classification

Goal: use SQLite as the queryable source of truth for virtual views.

Implemented:

- SQLite tables for media items, tags, operations, timeline segments, similarity groups, parser templates, transcripts, feedback, and calibrators.
- Summary API aggregates media counts and `size_bytes` by media type for virtual dashboard storage views.
- Metadata indexing from organized media and manifests.
- Filename parsing fields for author, person, platform, series, code, scene, quality, original name, normalized path, and risk state.
- Virtual library search and filtering.
- Author and face-group management without requiring users to browse raw NAS folders.
- Original filename preservation fields and move-history fallback logic.

Validation after NAS full run:

- Check media row count against files under `/media`.
- Confirm `original_name` is populated from the earliest known source for a sample of renamed files.
- Confirm virtual search can filter by media type, author, tag, and transcript text.

## Phase 3: Vision Tags and Video Understanding

Goal: classify media by visual content, not only filenames.

Implemented:

- Frame extraction with resumable cache behavior.
- Dynamic video frame extraction by duration, plus generated contact-sheet overview images for video detail pages.
- Local face scanning and conservative clustering.
- OpenCLIP-based vision labels for scene, clothing/style, shooting method, content type, and related tags.
- Vision index import into `media_tags` and `media_timeline_segments`.
- Manual tag feedback and lightweight calibrator training hook.
- Strong-model rescan command for low-confidence media.

Validation after NAS full run:

- Confirm `vision_labels.csv`, `frame_index.csv`, and timeline rows are populated.
- Confirm longer videos receive more cached frames than short videos and expose `contact_sheet` in `frame_index.csv`.
- Inspect top visual tags and low-confidence review items.
- Confirm media details show tags and timeline segments when available.
- Confirm manually confirmed/rejected tags persist and calibrator training records data.

## Phase 4: Deduplication, Similarity, and Versions

Goal: identify duplicates and near-duplicates without destructive deletion.

Implemented:

- Exact duplicate workflow.
- Similarity index from hashes and keyframe-derived signals.
- Similarity group tables and UI.
- Safe-delete operation that moves media to review instead of destroying files.
- Review cleanup and duplicate staging commands.

Validation after NAS full run:

- Confirm duplicate and similarity groups are generated.
- Review a sample of groups for same-file, resized, watermarked, and partial-content cases.
- Confirm no files are physically deleted by the Web delete action.

## Phase 5: Privacy, Compliance, Models, and Performance

Goal: make the system private, maintainable, and performant on NAS hardware.

Implemented:

- Local-only model execution and model management page.
- Persistent `/models` volume with official/default URLs, custom URLs, and runtime cache markers.
- Access password support.
- Operation audit log.
- Subtitle generation from transcripts, including original and bilingual VTT output paths.
- Separate transcript engine and audio-tag mode so full subtitles do not require full SenseVoice audio tagging.
- Intel iGPU/OpenVINO and FFmpeg VAAPI settings.
- Docker images separated by base, vision, clip, and transcribe capabilities.

Validation after NAS full run:

- Confirm all required model cards show correct status and nonzero size when cached.
- Confirm video playback exposes subtitle tracks when transcript/subtitle files exist.
- Confirm subtitles are time-aligned with playback, not only stored as one full-text transcript block.
- Confirm transcript detail can show segment timestamps and that the selected subtitle track uses a consistent primary language.
- Confirm CPU/GPU settings are reflected in jobs and do not stall progress.
- Confirm audit logs are newest-first and include manual edits, favorites, deletes, merges, and workflow jobs.

## Post-Full-Run NAS Validation Checklist

Run after the current full-library job finishes:

```bash
python3 scripts/phase_audit.py --db /volume1/docker/tg-media-manager/data/tg_media_manager.sqlite3 --media-root /volume4/BS-Secondary/BS-Media2/BS-Lsp/Tgdownloads/LSP
```

Expected outputs:

- Phase checklist with code-level status.
- Database table counts.
- Media, tag, timeline, transcript, similarity, and operation counts.
- Manifest/subtitle/cache file counts.
- Warnings for missing expected outputs.

## Known Deferred Work

- Web model-pack manifest installer is recorded in `docs/architecture-model-management.md` but not fully implemented yet.
- Local model upload through the Web UI is still future work.
- Subtitle quality pass: current detail text is a plain transcript block and some ASR outputs fall back to a single untimed segment. Add timestamped segment display, reject or mark untimed ASR outputs, prefer a timestamp-capable subtitle engine for full subtitles, and keep mixed-language output out of the default subtitle track.
- Non-Chinese subtitle translation depends on a future local translation model/runtime selection; translated/bilingual output should be optional and separate from the original-language track.
- Vision calibrators exist as a training hook; production-quality custom model training/export remains a later cycle.

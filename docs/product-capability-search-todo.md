# TG Media Manager Product TODO Audit

Date: 2026-07-07

This document records the product direction discussed for the media search and capability center rebuild. It is intentionally tied to implementation checkpoints so later versions can audit what is complete and what still needs real model work.

## Capability Center

Status: Implemented, with vector/VLM model execution still staged.

- Done: Models page now includes a capability center split into core/system capabilities and downloadable model capabilities.
- Done: Each capability shows purpose, source, readiness, size, and whether it is deleteable.
- Done: Capabilities covered: filename parsing, thumbnails/frame extraction, face clustering, scene/clothing labels, speech-to-text, subtitles, vector search, and VLM image understanding.
- Done: Model registry includes OpenCLIP, InsightFace, SenseVoice, Fun-ASR-Nano, faster-whisper, custom detector, BGE, FastViT, DeepLabV3, and VLM placeholders.
- Partial: BGE/FastViT/DeepLab/VLM downloads require user-provided URLs or future default model pack manifests.

## Search First

Status: Implemented for structured, lexical, and lightweight local semantic search.

- Done: Quick Find is now the first navigation entry and default page.
- Done: Keyword, tag, author, subtitle/transcript, media type, favorite, face group, duration, and resolution filters are available.
- Done: Natural-language-lite preprocessing converts common phrases like duration and resolution into structured filters.
- Done: Saved searches are stored in SQLite and can be reused/deleted from the Quick Find page.
- Done: Media library and random waterfall keep existing infinite-scroll behavior and media grid controls.
- Done: Lightweight local semantic ranking is available through the `media_embeddings` table and `/api/media?semantic=true`.
- Done: Similar media lookup is available through `/api/media/{id}/similar` using local image/text embeddings.
- Partial: Full CLIP/BGE nearest-neighbor ranking can replace the lightweight local vectors once those models are installed.

## Local Processing Trust

Status: Implemented in diagnostics/settings/model surfaces.

- Done: Diagnostics shows local-only status, media root, database path, model root, model download status, and remote model status.
- Done: Settings keeps compute, decode, OpenVINO, face, speech, model, monitor, and privacy controls visible.
- Done: Model page clarifies that models live under `/models` and are not baked into the Docker image.
- Done: Operations remain logged through jobs and media operations.

## Diagnostics Page

Status: Implemented and expanded.

- Done: Shows total media, photos/videos/other, metadata rows, dimensions, resolution, video duration, tags, transcripts, timed subtitles, subtitles files, face tags, thumbnails, and thumbnail health.
- Done: Shows missing models and recent failed jobs.
- Done: Shows recommendations when coverage falls below target.
- Done: Thumbnail health repair action is available.
- Partial: Diagnostic explanations are now visible through cards and recommendations; future versions can add per-media drill-down lists for each missing coverage bucket.

## Model Strategy

Status: Recorded and represented in the model registry.

- Done: SenseVoice/Fun-ASR/Whisper are speech engines.
- Done: InsightFace/ArcFace covers face vectors and clustering.
- Done: OpenCLIP covers visual labels and visual vector foundation.
- Done: BGE is represented for text vectors.
- Done: FastViT, DeepLabV3, and VLM are represented as optional heavy/advanced models.
- Done: Product strategy is light models for full-library work, heavy models for low-confidence, selected, or manual triggers.
- Done: Unified vector storage is staged through `media_embeddings`.

## Phase A: Base Index

Status: Implemented.

- Done: Metadata backfill supports duration, width, height, resolution, codec, frame rate, bit rate, container, and file size/index fields.
- Done: Thumbnail health check and batch repair exist.
- Done: Damaged thumbnail cache can be rebuilt.

## Phase B: Quick Find

Status: Implemented.

- Done: Main search box, advanced filters, tag/author/face/duration/resolution/favorite/subtitle filters, waterfall/grid results, and saved searches.

## Phase C: Models / Capability Center

Status: Implemented.

- Done: Ready/missing/downloading/error model status, size, path, purpose, recommended status, source URL override, recommended model install, and capability matrix.
- Partial: "One-click diagnose" is handled by Diagnostics page rather than a separate model-card button.

## Phase D: System Diagnostics

Status: Implemented.

- Done: Missing coverage, thumbnail health, subtitle timestamp coverage, failed jobs, unavailable models, privacy/runtime paths, and next actions.
- Partial: Per-media failure drill-down is a future enhancement.

## Phase E: Semantic Search

Status: Implemented with lightweight local vectors; heavy model vectors remain an upgrade path.

- Done: `media_embeddings` table added for text, image, subtitle, and tag vectors.
- Done: Model registry includes BGE and VLM entries.
- Done: Quick Find performs natural-language-lite parsing plus transcript/tag search.
- Done: `index-semantic` builds local hash text/subtitle vectors and perceptual image vectors without downloading models.
- Done: Full-library workflow now ends with semantic index refresh.
- Done: `/api/media?semantic=true` ranks results by local semantic vectors while preserving core filters.
- Done: `/api/media/{id}/similar` returns nearby media from local text/image vectors.
- Pending: Replace lightweight vectors with BGE text vectors and CLIP image vectors when the selected model pack is ready.

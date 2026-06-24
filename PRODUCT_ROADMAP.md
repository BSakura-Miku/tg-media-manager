# TG Media Manager Product Roadmap

## Product Direction

TG Media Manager is evolving from a Telegram download sorter into a local-first private media asset manager.

Core product principles:

- Local-first: analysis, tags, face grouping, thumbnails, and metadata stay on the NAS/local machine.
- Virtual classification first: categories, tags, authors, people, sources, quality, and risk views are database/index views, not a reason to endlessly move files.
- Stable physical storage: original media should live in a predictable normalized library layout with reversible operations.
- Web-first consumption: users should browse images, play videos, inspect tags, edit authors, and review risk items in the Web UI, not in raw NAS folders.
- Conservative automation: high-confidence results can be applied, medium-confidence results go to review, low-confidence results are recorded but not trusted.
- Compliance and safety first: suspicious underage/illegal/risky material is isolated, not mixed into normal library views.

## Physical Files vs Virtual Classification

Virtual classification does not mean leaving chaotic filenames forever.

Recommended physical layout:

```text
/media/
  _LIBRARY/
    Originals/
      YYYY/
        YYYY-MM/
          VID_YYYYMMDD_HHMMSS_<duration>_<resolution>_<hash8>.ext
          IMG_YYYYMMDD_HHMMSS_<resolution>_<hash8>.ext
  _MANIFESTS/
  _REVIEW/
  _QUARANTINE/
```

Physical filename goals:

- Stable.
- Collision-resistant.
- Short enough for SMB/NAS tools.
- Includes date, media type, duration/resolution when known, and hash.
- Original filename is preserved in metadata, never lost.

Virtual views shown in Web:

- Authors.
- People/FaceGroups.
- Tags.
- Scenes.
- Quality.
- Source platform.
- Timeline segments.
- Duplicates/similar media.
- Review queue.
- Risk quarantine.

## Web Playback and Viewing

The Web UI should become the primary library surface.

Required viewer features:

- Image lightbox with next/previous navigation.
- Video player with seek, poster frame, duration, resolution, tags, author/person links.
- Media detail panel with original filename, normalized filename, hash, tags, confidence, source, author/person, risk state, and operation history.
- Search result grid that opens directly into viewer.
- Tag and author edits from the detail view.
- Timeline view for analyzed videos.

This avoids needing compliant/meaningful folders on the NAS itself. NAS folders become storage; Web becomes the product experience.

## Phase 1: Product UX and Workflow Foundation

Goal: make the current tool understandable and operable.

Scope:

- Redesign dashboard around recommended workflows, status cards, and review queues.
- Author page sorting/filtering/table-card toggle.
- Fix missing thumbnails with cached author thumbnails and video-frame fallback.
- Human-readable job flows with next-step buttons.
- Face workflow wizard: extract frames -> face scan -> cluster -> report -> review -> apply.
- Scene workflow wizard: extract frames -> vision scan -> tag review -> apply.
- Author sync preview before applying directory changes.
- Stronger operation logs for rename, merge, exclude, sync, apply.

## Phase 2: Metadata Database and Virtual Classification

Goal: move from CSV-first manifests to a proper queryable metadata model.

Scope:

- SQLite metadata tables for media, files, authors, people, face groups, tags, tag assignments, operations, and virtual collections.
- Import existing CSV manifests into SQLite.
- File-name intelligent parser:
  - author
  - platform
  - series
  - ID/code
  - person
  - scene
  - keywords
  - resolution
  - date
- Filename parsing templates, for example:
  - `[author]-[person]-[theme]-[id]`
  - `[platform]_[author]_[date]_[resolution]`
  - `[author]_[person]_[scene]_[quality]_[date]`
- Virtual category pages:
  - Authors
  - People
  - Tags
  - Quality
  - Source
  - Review
  - Risk quarantine

## Phase 3: Vision Tags and Video Understanding

Goal: understand media contents beyond filename and poster frame.

Scope:

- Multi-level tag taxonomy:
  - Person features
  - Scene environment
  - Clothing/style
  - Shooting method
  - Content type
  - Quality parameters
  - Source platform
  - Author information
- Tag assignment with confidence and source:
  - filename
  - vision
  - face
  - manual
- Tag states:
  - confirmed
  - pending
  - rejected
- Video keyframe extraction.
- Scene cut detection.
- Timeline segment labeling, for example:

```text
00:00-03:20 opening / selfie / indoor
03:20-12:40 indoor scene
12:40-18:10 uniform theme
18:10-30:00 ending segment
```

## Phase 4: Deduplication and Similarity

Goal: reduce clutter and identify versions/fragments without deleting by mistake.

Scope:

- Exact duplicate detection:
  - size + sha/md5
- Perceptual image hash.
- Video fingerprint from keyframes.
- Similarity groups:
  - same content, different filename
  - different resolution versions
  - cropped version
  - watermarked version
  - partial clip from longer video
- Duplicate review UI:
  - keep highest quality suggestion
  - keep original/source-preferred suggestion
  - move duplicates to review/quarantine

## Phase 5: Privacy, Compliance, and Safety

Goal: make the product safe to use and maintain.

Scope:

- Access password.
- Local-only processing statement.
- Operation audit log.
- Sensitive folder lock.
- Database backup/export.
- Risk detection and isolation:
  - suspected underage terms/content
  - suspected illegal/risky content
  - unknown-risk review queue
- User confirmation of lawful source.
- No redistribution reminder.
- Risk items must not be auto-added to normal library views.

## Current Priorities

Current execution status is tracked in:

```text
docs/phase-execution-plan.md
```

Phase execution sequence:

1. Phase 1: UX and workflow foundation.
2. Phase 2: metadata database and virtual classification.
3. Phase 3: vision tags and video understanding.
4. Phase 4: dedupe, similarity, and version review.
5. Phase 5: privacy, compliance, models, and performance.

Run the local phase audit with:

```bash
make phase-audit
```

After the NAS full-library job finishes, run the same audit with the NAS database and media root:

```bash
python3 scripts/phase_audit.py --db /volume1/docker/tg-media-manager/data/tg_media_manager.sqlite3 --media-root /volume4/BS-Secondary/BS-Media2/BS-Lsp/Tgdownloads/LSP
```

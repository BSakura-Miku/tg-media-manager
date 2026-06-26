# UI Audit Report

Date: 2026-06-26
Target: NAS production UI at `http://10.10.2.10:8787`
Version audited: v1.0.8, with fixes prepared for v1.0.9

## Scope

Checked the main TG Media Manager surfaces:

- Overview
- Jobs
- Library
- Tag Graph
- Random Flow
- Models
- Authors
- Face Groups
- Logs
- Settings
- Media detail viewer
- Mobile overview, library, jobs, settings, random flow

Screenshots are saved in this folder as numbered PNG files.

## Method

- Chrome screenshot audit at 1440x1000 desktop.
- Chrome screenshot audit at 390x844 mobile.
- DOM checks for horizontal overflow, small click targets, page errors, media card counts, and key headings.
- Non-destructive interaction checks for navigation, search, detail opening, filters, theme/language/refresh, model page, authors, and media detail.

## Findings

### 1. Overview

Health: Good.

Strengths:

- Brand, version, navigation, stats, graph, recent media, tasks, and storage are discoverable.
- Desktop has no horizontal overflow.
- Mobile reflows into a usable one-column hierarchy.

Issues found:

- Mobile dashboard soft-link buttons such as "View all" were 34px tall, below the intended 44px touch target.

Fix:

- Raised `.softLink` minimum height to 44px.

### 2. Jobs

Health: Good.

Strengths:

- Jobs are grouped by state.
- Running, warning, error, cancelled, and completed states are visibly distinct.
- Details wrap long paths without horizontal page overflow.

Residual watch item:

- Very old failed jobs remain visible, which is correct historically but can make the page feel noisy. Consider a later "archive old completed/failed jobs" view option.

### 3. Library

Health: Good.

Strengths:

- Masonry media cards preserve original thumbnail ratios.
- Overlay pills avoid the old large text block that covered thumbnails.
- Search and media detail entry are discoverable.

Residual watch item:

- Some source thumbnails are visually corrupted/yellow-green because the underlying generated thumbnail file is bad. This should be handled by the thumbnail repair queue rather than UI styling.

### 4. Tag Graph

Health: Good.

Strengths:

- Graph is interactive and no longer static-looking.
- Text and nodes are readable in dark mode.
- Zoom controls and edge threshold controls are visible.

Residual watch item:

- Dense graph states can still feel busy. Later improvement: add category toggles and focus mode.

### 5. Random Flow

Health: Good.

Strengths:

- Uses the same media card system as Library.
- Infinite loading is stable with seeded random pagination.
- No horizontal overflow on desktop or mobile.

### 6. Models

Health: Good after minor polish.

Strengths:

- Model state, size, path, URL env, and actions are visible.
- Download/delete controls are clear and separated.

Issue found:

- Light-mode model metadata rows looked too heavy/gray.

Fix:

- Added a lighter model metadata row treatment in light mode.

### 7. Authors

Health: Good.

Strengths:

- Author cards and author detail browsing are clear.
- Card click opens a media browsing view.

Residual watch item:

- For authors without thumbnails, fallback cards are functional but visually plain. Later improvement: generate deterministic initials/avatar tiles.

### 8. Face Groups

Health: Good.

Strengths:

- Face cards show direct visual browsing and no old black overlay artifact.
- Click into a group is clear.

Residual watch item:

- Merge suggestions still require careful manual review; UI should keep strong visual confirmation before merging.

### 9. Logs

Health: Good.

Strengths:

- Log list has status filters.
- Full stdout/stderr remains on-demand through job detail, avoiding large default payloads.

### 10. Settings

Health: Good.

Strengths:

- Directory, monitor, privacy, and compute/model related options are grouped.
- Checkbox controls meet minimum size after the prior v1.0.8 QA pass.

### 11. Media Detail Viewer

Health: Fixed.

Strengths:

- Viewer opens in the current viewport and does not require scrolling back to the top.
- Favorite, rebuild thumbnail, delete, close, author edit, manual tag, tags, timeline, subtitles, and metadata are grouped.

Issues found:

- If `contact_sheet` exists in metadata but the actual image endpoint fails, the browser showed a broken image icon.
- Escape key did not close the media detail modal.
- Close icon had no explicit title.

Fixes:

- Added video overview image error fallback.
- Added `Esc` close handling.
- Added close button title.

## Accessibility Notes

Confirmed from screenshots/DOM:

- No horizontal overflow in audited pages.
- Main buttons and inputs are above the small-control threshold after fixes.
- Focus-visible styling exists globally.
- Reduced-motion CSS exists globally.

Not fully verified:

- Screen reader announcements and complete keyboard traversal require manual assistive tech testing.
- Color contrast was assessed visually and through design-system rules, not through a full WCAG contrast scanner.

## Screenshots

- `01-overview-desktop.png`
- `02-jobs-desktop.png`
- `03-library-desktop.png`
- `04-tag-graph-desktop.png`
- `05-random-flow-desktop.png`
- `06-models-desktop.png`
- `07-authors-desktop.png`
- `08-faces-desktop.png`
- `09-logs-desktop.png`
- `10-settings-desktop.png`
- `11-media-viewer-desktop.png`
- `15-overview-mobile.png`
- `16-library-mobile.png`
- `17-jobs-mobile.png`
- `18-settings-mobile.png`
- `19-random-mobile.png`
- `20-models-interaction.png`
- `21-author-interaction.png`

## Follow-up Backlog

- Add thumbnail repair queue for visually corrupted thumbnails.
- Add a graph focus/category mode for dense tag graphs.
- Add optional job-history archive filters for old failed/completed jobs.
- Improve fallback visuals for authors without thumbnails.

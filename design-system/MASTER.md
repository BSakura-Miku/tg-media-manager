# TG Media Manager Design System

Version: 1.0

## Product Position

TG Media Manager is a private, local-first media library console for large personal photo/video collections. The UI must feel like a calm pro media workstation: content-first, fast, readable, privacy-aware, and comfortable for long browsing sessions.

This is not a marketing landing page. Avoid oversized hero sections, decorative illustration, and copy-heavy onboarding. The first screen should always expose useful library state or usable controls.

## Core Principles

- Content first: thumbnails, metadata, tasks, and tags are the primary material.
- Local and private: actions that expose, delete, move, or scan media must be explicit and logged.
- Dense but breathable: support thousands of media items without making the interface feel cramped.
- Fast perceived response: lists and media grids should progressively load, reserve space, and avoid layout jumps.
- Clear status: running, warning, error, cancelled, and completed states must be visually and textually distinct.

## Visual Style

- Primary style: dark cinematic glass, restrained glow, high contrast.
- Light mode: same structure, quieter surfaces, stronger text contrast, less glow.
- Avoid pure one-color palettes. Use a neutral dark base with blue, cyan, violet, green, amber, and red as semantic accents.
- Do not use emoji as structural icons. Use lucide-react or project SVG assets.

## Color Tokens

Use semantic tokens in CSS rather than hard-coded component colors:

- `--bg`: app background.
- `--panel`: main card/surface.
- `--panel-2`: inset surface.
- `--line`: normal border.
- `--line-strong`: emphasized border.
- `--text`: primary text.
- `--soft`: secondary readable text.
- `--muted`: tertiary text.
- `--accent`: primary action/focus.
- `--good`: success/completed.
- `--warn`: warning/cancelled/stale.
- `--bad`: error/destructive.

Contrast targets:

- Primary text: WCAG AA 4.5:1 minimum.
- Secondary text: 3:1 minimum.
- Icon-only buttons: 3:1 minimum and a visible focus state.

## Typography

- Font stack: Inter first, then system UI.
- Body text should not go below 13px on desktop or 16px in mobile form inputs.
- Use tabular numbers for counts, durations, progress, storage, and job IDs.
- Long file paths and filenames should wrap with `overflow-wrap: anywhere`; never force horizontal page scroll.

## Layout

- Desktop: persistent sidebar, content max width, dense dashboard cards.
- Tablet: keep sidebar if width allows; reduce grid columns before shrinking text.
- Mobile: one-column media grid, controls wrap, no horizontal scrolling.
- Keep primary touch targets at least 44px tall/wide.
- Avoid nested scrolling except code/log blocks and modal bodies.

## Media Cards

- Preserve the original thumbnail ratio whenever known.
- Show low-cost thumbnails in lists; load the original media only in the viewer.
- Overlay metadata as compact readable pills. Do not cover large portions of the thumbnail.
- If a thumbnail fails, show a clear fallback tile and allow rebuilding from the detail view.

## Jobs And Logs

- Job lists must use summary payloads only. Full stdout/stderr loads on demand.
- Group tasks by status: running, warning, error, completed, other.
- Show workflow step number and remaining steps for multi-stage workflows.
- Logs show newest first and include timestamps when available.
- Stop/cancel actions must preserve cached outputs and allow resume/retry when possible.

## Tag Graph

- Nodes scale text and circle together.
- Interaction must support click-to-filter, drag/pan, zoom, and visible focus.
- In light mode, labels must stay readable on node fills.
- Use the graph as navigation, not decoration: clicking a node or edge should produce media results.

## Motion

- Use 150-300ms for small interactions and under 420ms for larger page/card transitions.
- Animate transform and opacity, not width/height/top/left.
- Respect `prefers-reduced-motion`.
- Motion should explain state changes: opening media, filtering, loading more, and status transitions.

## Accessibility QA

Before each UI release:

- Keyboard focus is visible on buttons, inputs, media cards, graph controls, and modal close buttons.
- Icon-only buttons have labels or titles.
- Modals can be closed with an explicit visible control.
- Destructive actions are separated and confirmed.
- 375px mobile, 768px tablet, 1440px desktop, and light/dark modes are checked.

## Performance QA

- Use cached thumbnails in grids.
- Lazy load images below the fold.
- Avoid returning large logs in polling endpoints.
- Use stable dimensions or aspect ratios for cards.
- Infinite lists should append predictably without duplicate pages.

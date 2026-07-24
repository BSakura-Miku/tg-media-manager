# Subtitle Pipeline v1.5 (local candidate)

Deployed to the NAS on 2026-07-23 as
`tg-media-manager:nas-1.5.0-amd64`.

## Design inputs

The iteration reviewed two active open-source projects:

- VideoCaptioner separates transcription, word-timestamp alignment, semantic
  splitting, text correction, and translation. TG Media Manager adopts the
  separation of concerns and measurable subtitle post-processing, but does not
  copy GPL code or send private transcripts to a remote LLM.
- Subgen emphasizes idempotent queueing, audio-offset compensation, controlled
  concurrency, timeouts, and skip/retry behavior. TG Media Manager already had
  offset compensation and a single active job; v1.5 adds media/config
  fingerprints, durable attempt state, retry backoff, and permanent-failure
  classification.

## Readability and quality

Word-level timestamps are still the source of truth. Post-processing now:

- gives short cues at least 0.8 seconds of display time where the following cue
  leaves room;
- never extends a cue across the next cue;
- preserves original word timestamps while recording cue-level mean confidence;
- calculates overlap, reading speed, very short cues, adjacent repetition, and
  low-confidence word ratios;
- stores the quality report with the transcript and shows it in the media
  viewer.

The report is a review signal, not an accuracy score. A high-confidence
recognition can still contain the wrong word, so model comparisons still need a
private reference transcript and character error rate (CER).

## Decode controls

The Faster-Whisper adapter now records and fingerprints:

```text
WHISPER_VAD_THRESHOLD=0.5
WHISPER_MIN_SILENCE_MS=500
WHISPER_NO_SPEECH_THRESHOLD=0.6
WHISPER_LOG_PROB_THRESHOLD=-1.0
WHISPER_COMPRESSION_RATIO_THRESHOLD=2.4
SUBTITLE_MIN_SECONDS=0.8
```

Existing language, prompt, beam size, stable timestamps, cue length, duration,
and silence-gap options remain supported.

## Durable retry state

Schema version 5 adds `media_transcription_state`. Each attempt stores:

- a fingerprint of the media identity and every result-affecting ASR option;
- status, attempt count, engine, model, last error, and timestamps;
- exponential retry time for temporary failures;
- a permanent-failure state for missing files and clear no-audio/invalid-media
  failures.

Changing the media or ASR configuration produces a new fingerprint and makes
the item eligible again. This prevents a small set of bad files from occupying
every sample batch. A non-Whisper engine may still save useful transcript text
without timestamps; that partial result is retained, but its state enters
backoff until a timed-subtitle fallback is available. The state records the
engine and model that actually produced the result.

## Benchmark

Run the fixed local sample set:

```bash
.venv/bin/python scripts/benchmark_subtitles.py \
  .local/benchmarks/subtitle-samples \
  --models medium large-v3-turbo \
  --output-dir .local/benchmarks/subtitle-results-v15 \
  --model-root .local/models/whisper
```

For objective text accuracy, keep private reference transcripts outside Git and
pass their JSON file using `--references`. The benchmark reports CER plus the
readability diagnostics above.

The July 23 local run used four private Telegram clips on the Mac mini:

| Model | Realtime-factor range | Practical conclusion |
| --- | ---: | --- |
| `medium` | 0.16-0.60 | Fast enough for the default queue and generally stable. |
| `large-v3-turbo` | 0.19-0.73 | Corrected some words, but also regressed others; use as a selective review pass. |

`WHISPER_MIN_SILENCE_MS=500` changed cue boundaries and improved individual
words in some clips, but was not uniformly more accurate. The default therefore
remains `medium`; a quality warning means "review this result", not "replace it
automatically with the larger model". No private media, transcripts, or
benchmark outputs are checked into Git.

## Rollout boundary

Before a NAS rollout:

1. create and verify an online SQLite backup;
2. run a 3-10 item transcription batch;
3. inspect every quality warning and compare selected samples with references;
4. verify the schema migration and transcription-state counts;
5. only then increase the batch size.

## Production deployment

- Previous image retained: `tg-media-manager:nas-1.4.0-amd64`
- Pre-migration backup:
  `data/backups/tg_media_manager_pre_v1.5.0_20260723_2338.sqlite3`
- Post-migration backup:
  `data/backups/tg_media_manager_post_v1.5.0_20260723_2346.sqlite3`
- Compose and environment rollback snapshots:
  `compose-backups/docker-compose.yaml.pre-v1.5.0.20260723_2338` and
  `compose-backups/.env.pre-v1.5.0.20260723_2338`

Both database backups passed checksum, SQLite integrity, and temporary-restore
verification. Production migrated from schema 4 to schema 5 with 14,061 media
rows and 7,011 transcript rows intact. The container health check, public
version endpoint, frontend entry point, static asset, and authentication
boundary were verified after deployment.

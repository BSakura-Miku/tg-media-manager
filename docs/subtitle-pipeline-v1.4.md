# Subtitle Pipeline v1.4

Deployed to the NAS on 2026-07-23 as `tg-media-manager:nas-1.4.0-amd64`.

## Why It Changed

The previous production path used Faster-Whisper `base` for timed fallback and
wrote raw model segments directly to VTT. Production data contained about 6,991
SenseVoice text-only transcripts and only 20 Faster-Whisper timed transcripts.

v1.4 adds a `stable-faster-whisper` path with:

- Faster-Whisper word timestamps and Stable-TS silence suppression
- readable CJK cue regrouping (24 characters, 7 seconds, 0.8-second silence gap)
- audio stream start-time compensation
- configurable model, compute type, beam size, language, and vocabulary prompt
- retained word-level timing in `segments_json`
- bilingual VTT creation only when a real translation exists

The old `auto`, `sensevoice-gguf`, and `faster-whisper` engines remain available
as rollback choices.

## Local Benchmark

Four read-only NAS samples (English and Mandarin, 14-55 seconds) were copied to
the Mac mini and tested with identical beam and subtitle settings.

| Model | Mac real-time factor | Result |
| --- | ---: | --- |
| `base` | 0.02-0.09 | Fast, but produced severe Mandarin word errors |
| `medium` | 0.15-0.52 | Large accuracy improvement; selected default |
| `large-v3-turbo` | 0.18-0.69 | Better on some vocabulary, about 50% slower on short clips |

Example: `base` recognized the lyric “一群小小的羊……美美地晒太阳” as
“一群傻傻不断……打操人生”; `medium` recovered the main sentence.

The NAS-native amd64 image transcribed a 14.19-second Mandarin sample in 18.91
seconds with a four-CPU limit (real-time factor 1.33). The model loaded from the
persistent `/models/whisper` cache and produced two timed cues.

## Verification

- 43 Python tests passed
- frontend production build passed
- Compose configuration and Python compilation passed
- amd64 image dependency import passed:
  - Stable-TS 2.19.1
  - Faster-Whisper 1.2.1
  - Torch/Torchaudio 2.3.1 CPU
- temporary-container health, version, and authentication checks passed
- production database integrity check returned `ok`
- production health and version endpoints returned v1.4.0

## Production Defaults

```text
TRANSCRIPT_ENGINE=stable-faster-whisper
WHISPER_MODEL=medium
WHISPER_COMPUTE_TYPE=int8
WHISPER_BEAM_SIZE=5
SUBTITLE_MAX_CHARS=24
SUBTITLE_MAX_SECONDS=7
SUBTITLE_MAX_GAP=0.8
```

Use `small` for preview batches and `large-v3-turbo` for selected quality reruns.
Do not start a full-library backfill until a staged batch has been reviewed.

## Rollback Boundary

Deployment backup timestamp: `20260723_203337`.

- Database backup:
  `data/backups/tg_media_manager_pre_v1.4.0_20260723_203337.sqlite3`
- Compose backup:
  `compose-backups/docker-compose.yaml.pre-v1.4.0.20260723_203337`
- Environment backup:
  `compose-backups/.env.pre-v1.4.0.20260723_203337`
- Previous image retained:
  `tg-media-manager:nas-1.3.0-amd64`

All paths above are relative to `/volume1/docker/tg-media-manager` on the NAS.

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gc
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.metadata import (
    extract_audio_wav,
    load_faster_whisper_model,
    transcript_to_vtt,
    transcribe_with_faster_whisper,
)


def media_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def normalized_transcript(text: object) -> str:
    return re.sub(r"[\W_]+", "", str(text or "").lower(), flags=re.UNICODE)


def character_error_rate(reference: object, hypothesis: object) -> float | None:
    expected = normalized_transcript(reference)
    actual = normalized_transcript(hypothesis)
    if not expected:
        return None
    previous = list(range(len(actual) + 1))
    for row_index, expected_char in enumerate(expected, start=1):
        current = [row_index]
        for column_index, actual_char in enumerate(actual, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column_index] + 1,
                    previous[column_index - 1] + (expected_char != actual_char),
                )
            )
        previous = current
    return round(previous[-1] / len(expected), 4)


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark TGMM subtitle models on local media samples.")
    parser.add_argument("sample_dir", type=Path)
    parser.add_argument("--models", nargs="+", default=["base", "medium"])
    parser.add_argument("--output-dir", type=Path, default=Path(".local/benchmarks/subtitle-results"))
    parser.add_argument("--model-root", type=Path, default=Path(".local/models/whisper"))
    parser.add_argument(
        "--references",
        type=Path,
        help="Optional private JSON mapping sample filenames to reference transcripts.",
    )
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    samples = sorted(
        path for path in args.sample_dir.iterdir() if path.suffix.lower() in {".mp4", ".mov", ".mkv", ".m4v"}
    )
    if args.limit > 0:
        samples = samples[: args.limit]
    if not samples:
        raise SystemExit("No media samples found")
    references: dict[str, object] = {}
    if args.references:
        references = json.loads(args.references.read_text(encoding="utf-8"))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    wav_dir = args.output_dir / "wav"
    wav_dir.mkdir(parents=True, exist_ok=True)
    args.model_root.mkdir(parents=True, exist_ok=True)
    os.environ["WHISPER_MODEL_ROOT"] = str(args.model_root.resolve())
    os.environ.setdefault("WHISPER_DEVICE", "cpu")
    os.environ.setdefault("WHISPER_COMPUTE_TYPE", "int8")
    os.environ.setdefault("WHISPER_BEAM_SIZE", "5")
    os.environ.setdefault("SUBTITLE_MAX_CHARS", "24")
    os.environ.setdefault("SUBTITLE_MAX_SECONDS", "7")
    os.environ.setdefault("SUBTITLE_MAX_GAP", "0.8")

    durations: dict[Path, float] = {}
    for sample in samples:
        durations[sample] = media_duration(sample)
        wav = wav_dir / f"{sample.stem}.wav"
        if not wav.exists():
            ok, error = extract_audio_wav(sample, wav)
            if not ok:
                raise RuntimeError(f"Audio extraction failed for {sample.name}: {error}")

    summary: list[dict] = []
    for model_name in args.models:
        started_loading = time.perf_counter()
        model = load_faster_whisper_model(model_name, stable_timestamps=True)
        load_seconds = time.perf_counter() - started_loading
        for sample in samples:
            wav = wav_dir / f"{sample.stem}.wav"
            started = time.perf_counter()
            result = transcribe_with_faster_whisper(
                wav,
                model,
                model_name,
                stable_timestamps=True,
            )
            elapsed = time.perf_counter() - started
            model_dir = args.output_dir / model_name
            model_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "sample": sample.name,
                "audio_seconds": round(durations[sample], 3),
                "elapsed_seconds": round(elapsed, 3),
                "realtime_factor": round(elapsed / durations[sample], 3) if durations[sample] else None,
                **result,
            }
            (model_dir / f"{sample.stem}.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (model_dir / f"{sample.stem}.vtt").write_text(
                transcript_to_vtt(result["segments"], result["text"]),
                encoding="utf-8",
            )
            row = {
                "model": model_name,
                "sample": sample.name,
                "language": result["language"],
                "audio_seconds": round(durations[sample], 2),
                "elapsed_seconds": round(elapsed, 2),
                "realtime_factor": round(elapsed / durations[sample], 2) if durations[sample] else None,
                "cues": len(result["segments"]),
                "characters": len(result["text"].replace("\n", "")),
                "load_seconds": round(load_seconds, 2),
                "quality": result.get("quality") or {},
            }
            reference = references.get(sample.name)
            if isinstance(reference, dict):
                reference = reference.get("text")
            if reference:
                row["character_error_rate"] = character_error_rate(reference, result["text"])
            summary.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
        del model
        gc.collect()

    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

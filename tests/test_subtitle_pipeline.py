from __future__ import annotations

import os
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from backend.app import metadata
from backend.app.subtitles import (
    contains_translation,
    normalize_language_code,
    regroup_word_segments,
    subtitle_quality_report,
)


class SubtitleGroupingTests(unittest.TestCase):
    def test_cjk_words_are_split_by_length_and_silence(self) -> None:
        segments = [
            {
                "words": [
                    {"start": 0.0, "end": 0.4, "word": "今"},
                    {"start": 0.4, "end": 0.8, "word": "天"},
                    {"start": 0.8, "end": 1.2, "word": "天"},
                    {"start": 1.2, "end": 1.6, "word": "气"},
                    {"start": 1.6, "end": 2.0, "word": "很"},
                    {"start": 2.0, "end": 2.4, "word": "好"},
                    {"start": 2.4, "end": 2.6, "word": "。"},
                    {"start": 4.0, "end": 4.4, "word": "出"},
                    {"start": 4.4, "end": 4.8, "word": "门"},
                    {"start": 4.8, "end": 5.2, "word": "散"},
                    {"start": 5.2, "end": 5.6, "word": "步"},
                ]
            }
        ]
        cues = regroup_word_segments(segments, "Chinese", max_chars=6, max_gap=0.8)
        self.assertEqual(normalize_language_code("Chinese"), "zh")
        self.assertEqual([cue["text"] for cue in cues], ["今天天气很好。", "出门散步"])
        self.assertTrue(all("words" in cue for cue in cues))

    def test_word_timestamps_receive_audio_stream_offset(self) -> None:
        cues = regroup_word_segments(
            [{"words": [{"start": 0.2, "end": 0.8, "word": " hello."}]}],
            "English",
            offset_seconds=1.5,
        )
        self.assertEqual(cues[0]["start"], 1.7)
        self.assertEqual(cues[0]["end"], 2.5)
        self.assertEqual(cues[0]["words"][0]["start"], 1.7)
        self.assertEqual(cues[0]["words"][0]["end"], 2.3)

    def test_short_cue_receives_reading_time_without_overlapping_next_cue(self) -> None:
        cues = regroup_word_segments(
            [
                {"words": [{"start": 0.0, "end": 0.2, "word": "你好", "probability": 0.9}]},
                {"words": [{"start": 0.9, "end": 1.2, "word": "世界", "probability": 0.8}]},
            ],
            "Chinese",
            max_gap=0.5,
            min_seconds=0.8,
        )
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[0]["end"], 0.8)
        self.assertAlmostEqual(cues[1]["end"] - cues[1]["start"], 0.8)
        self.assertEqual(cues[0]["confidence"], 0.9)

    def test_quality_report_flags_overlap_repetition_and_low_confidence(self) -> None:
        report = subtitle_quality_report(
            [
                {
                    "start": 0.0,
                    "end": 0.2,
                    "text": "重复重复重复",
                    "words": [{"word": "重复重复重复", "probability": 0.2}],
                },
                {
                    "start": 0.1,
                    "end": 0.3,
                    "text": "重复重复重复",
                    "words": [{"word": "重复重复重复", "probability": 0.3}],
                },
            ],
            "zh",
        )
        self.assertEqual(report["overlap_count"], 1)
        self.assertEqual(report["repeated_cue_count"], 1)
        self.assertIn("reading-speed", report["warnings"])
        self.assertIn("low-confidence", report["warnings"])

    def test_bilingual_file_is_only_needed_for_real_translation(self) -> None:
        self.assertFalse(contains_translation([{"text": "你好"}]))
        self.assertFalse(contains_translation([{"text": "你好", "translation_zh": "你好"}]))
        self.assertTrue(contains_translation([{"text": "hello", "translation_zh": "你好"}]))

    def test_atomic_subtitle_write_preserves_existing_file_on_replace_failure(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "1.vtt"
            path.write_text("old", encoding="utf-8")
            with patch.object(metadata.os, "replace", side_effect=OSError("disk unavailable")):
                with self.assertRaises(OSError):
                    metadata.atomic_write_text(path, "new")
            self.assertEqual(path.read_text(encoding="utf-8"), "old")
            self.assertEqual(list(path.parent.glob(".1.vtt.*.tmp")), [])

    def test_save_transcript_rolls_back_database_when_subtitle_write_fails(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(
            """
            CREATE TABLE media_items (id INTEGER PRIMARY KEY, root TEXT NOT NULL DEFAULT '');
            CREATE TABLE media_transcripts (
                media_id INTEGER PRIMARY KEY,
                language TEXT NOT NULL DEFAULT '',
                text TEXT NOT NULL DEFAULT '',
                segments_json TEXT NOT NULL DEFAULT '[]',
                model TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT '',
                quality_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE media_tags (
                media_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT '',
                confidence REAL NOT NULL DEFAULT 1.0,
                source TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL DEFAULT 'confirmed',
                PRIMARY KEY (media_id, tag, source)
            );
            CREATE TABLE media_operations (
                id INTEGER PRIMARY KEY,
                media_id INTEGER,
                operation TEXT NOT NULL,
                detail TEXT NOT NULL DEFAULT ''
            );
            INSERT INTO media_items (id, root) VALUES (1, '');
            """
        )
        result = {
            "text": "hello",
            "language": "en",
            "engine": "stable-faster-whisper",
            "segments": [{"start": 0.0, "end": 1.0, "text": "hello"}],
        }
        with patch.object(metadata, "write_subtitle_files", side_effect=OSError("disk unavailable")):
            with self.assertRaises(OSError):
                metadata.save_transcript(conn, 1, result, "small", include_text_tags=False)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM media_transcripts").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM media_operations").fetchone()[0], 0)
        conn.close()


class WhisperAdapterTests(unittest.TestCase):
    def test_stable_adapter_keeps_words_and_configured_options(self) -> None:
        class StableResult:
            language = "Chinese"

            def to_dict(self):
                return {
                    "language": "Chinese",
                    "segments": [
                        {
                            "start": 0,
                            "end": 1,
                            "text": "你好。",
                            "words": [
                                {"start": 0.0, "end": 0.4, "word": "你", "probability": 0.9},
                                {"start": 0.4, "end": 0.8, "word": "好", "probability": 0.8},
                                {"start": 0.8, "end": 1.0, "word": "。", "probability": 0.9},
                            ],
                        }
                    ],
                }

        class StableModel:
            options = None

            def transcribe(self, _audio, **options):
                self.options = options
                return StableResult()

        model = StableModel()
        with patch.dict(
            os.environ,
            {"WHISPER_BEAM_SIZE": "5", "WHISPER_LANGUAGE": "", "SUBTITLE_MAX_CHARS": "24"},
            clear=False,
        ):
            result = metadata.transcribe_with_faster_whisper(
                Path("sample.wav"),
                model,
                "medium",
                stable_timestamps=True,
            )
        self.assertEqual(result["engine"], "stable-faster-whisper")
        self.assertEqual(result["language"], "zh")
        self.assertEqual(result["segments"][0]["text"], "你好。")
        self.assertEqual(len(result["segments"][0]["words"]), 3)
        self.assertEqual(model.options["beam_size"], 5)
        self.assertTrue(model.options["word_timestamps"])
        self.assertFalse(model.options["regroup"])
        self.assertEqual(model.options["vad_parameters"]["threshold"], 0.5)
        self.assertEqual(model.options["vad_parameters"]["min_silence_duration_ms"], 500)
        self.assertEqual(model.options["no_speech_threshold"], 0.6)
        self.assertEqual(model.options["compression_ratio_threshold"], 2.4)

    def test_plain_adapter_also_requests_word_timestamps(self) -> None:
        segment = SimpleNamespace(
            start=0.0,
            end=1.0,
            text=" Hello.",
            words=[SimpleNamespace(start=0.0, end=1.0, word=" Hello.", probability=0.75)],
        )

        class PlainModel:
            options = None

            def transcribe(self, _audio, **options):
                self.options = options
                return iter([segment]), SimpleNamespace(language="en")

        model = PlainModel()
        result = metadata.transcribe_with_faster_whisper(Path("sample.wav"), model, "small")
        self.assertEqual(result["engine"], "faster-whisper")
        self.assertEqual(result["segments"][0]["text"], "Hello.")
        self.assertTrue(model.options["word_timestamps"])
        self.assertTrue(model.options["vad_filter"])

from __future__ import annotations

import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.app import metadata
from backend.app.subtitles import contains_translation, normalize_language_code, regroup_word_segments


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
        self.assertEqual(cues[0]["end"], 2.3)
        self.assertEqual(cues[0]["words"][0]["start"], 1.7)

    def test_bilingual_file_is_only_needed_for_real_translation(self) -> None:
        self.assertFalse(contains_translation([{"text": "你好"}]))
        self.assertFalse(contains_translation([{"text": "你好", "translation_zh": "你好"}]))
        self.assertTrue(contains_translation([{"text": "hello", "translation_zh": "你好"}]))


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

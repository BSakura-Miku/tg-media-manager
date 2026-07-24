from __future__ import annotations

import unittest

from scripts.benchmark_subtitles import character_error_rate, normalized_transcript


class SubtitleBenchmarkTests(unittest.TestCase):
    def test_normalization_ignores_spacing_case_and_punctuation(self) -> None:
        self.assertEqual(normalized_transcript(" Hello，世界! "), "hello世界")

    def test_character_error_rate_uses_reference_length(self) -> None:
        self.assertEqual(character_error_rate("abc", "abc"), 0.0)
        self.assertEqual(character_error_rate("abc", "adc"), 0.3333)
        self.assertIsNone(character_error_rate("", "anything"))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import re
from typing import Iterable


_CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_CJK_SPACE_RE = re.compile(
    r"(?<=[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff])\s+"
    r"(?=[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff])"
)
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,，。！？!?；;：:、…])")
_SENTENCE_END_RE = re.compile(r"(?:[。！？!?…]|(?<!\.)\.(?:[\"'”’）)]*)?)$")

_LANGUAGE_CODES = {
    "chinese": "zh",
    "mandarin": "zh",
    "japanese": "ja",
    "english": "en",
    "korean": "ko",
    "dutch": "nl",
    "french": "fr",
    "german": "de",
    "spanish": "es",
    "italian": "it",
    "portuguese": "pt",
    "russian": "ru",
}


def normalize_language_code(value: object) -> str:
    language = str(value or "").strip().lower()
    if not language:
        return ""
    return _LANGUAGE_CODES.get(language, language.split("-", 1)[0])


def clean_subtitle_text(value: object) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = _CJK_SPACE_RE.sub("", text)
    return _SPACE_BEFORE_PUNCT_RE.sub(r"\1", text)


def _read_value(item: object, name: str, default: object = None) -> object:
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _number(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _word_from(value: object, offset_seconds: float) -> dict | None:
    text = str(_read_value(value, "word", _read_value(value, "text", "")) or "")
    if not text.strip():
        return None
    start = max(0.0, _number(_read_value(value, "start")) + offset_seconds)
    end = max(start + 0.01, _number(_read_value(value, "end"), start + 0.01) + offset_seconds)
    word = {
        "start": round(start, 3),
        "end": round(end, 3),
        "word": text,
    }
    probability = _read_value(value, "probability", _read_value(value, "prob", None))
    if probability is not None:
        word["probability"] = round(_number(probability), 4)
    return word


def _text_for_words(words: Iterable[dict]) -> str:
    return clean_subtitle_text("".join(str(word.get("word") or "") for word in words))


def _visible_length(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def _polish_cue_timing(
    cues: list[dict],
    *,
    contains_cjk: bool,
    min_seconds: float,
    max_seconds: float,
) -> list[dict]:
    """Give short cues enough reading time without crossing the next cue."""
    if not cues:
        return cues
    minimum = max(0.4, min(float(min_seconds), float(max_seconds)))
    reading_rate = 12.0 if contains_cjk else 20.0
    gap = 0.08
    for index, cue in enumerate(cues):
        start = _number(cue.get("start"))
        end = max(start + 0.01, _number(cue.get("end"), start + 0.01))
        text = clean_subtitle_text(cue.get("text"))
        desired = max(minimum, _visible_length(text) / reading_rate)
        desired = min(float(max_seconds), desired)
        target_end = max(end, start + desired)
        if index + 1 < len(cues):
            next_start = _number(cues[index + 1].get("start"), target_end + gap)
            target_end = min(target_end, max(end, next_start - gap))
        cue["start"] = round(start, 3)
        cue["end"] = round(max(end, target_end), 3)
        words = cue.get("words") or []
        probabilities = [
            _number(word.get("probability"))
            for word in words
            if isinstance(word, dict) and word.get("probability") is not None
        ]
        if probabilities:
            cue["confidence"] = round(sum(probabilities) / len(probabilities), 4)
    return cues


def subtitle_quality_report(segments: Iterable[dict], language: object = "") -> dict:
    """Return inexpensive, model-independent subtitle readability diagnostics."""
    cues = [item for item in segments if isinstance(item, dict) and clean_subtitle_text(item.get("text"))]
    language_code = normalize_language_code(language)
    contains_cjk = language_code in {"zh", "ja", "ko"} or any(
        _CJK_RE.search(clean_subtitle_text(item.get("text"))) for item in cues
    )
    reading_rate = 12.0 if contains_cjk else 20.0
    overlap_count = 0
    fast_count = 0
    short_count = 0
    repeated_count = 0
    max_cps = 0.0
    low_confidence_words = 0
    total_confidence_words = 0
    previous_text = ""
    previous_end = 0.0
    for index, cue in enumerate(cues):
        text = clean_subtitle_text(cue.get("text"))
        start = _number(cue.get("start"))
        end = max(start, _number(cue.get("end"), start))
        duration = max(0.01, end - start)
        cps = _visible_length(text) / duration
        max_cps = max(max_cps, cps)
        if cps > reading_rate * 1.2:
            fast_count += 1
        if duration < 0.6:
            short_count += 1
        if index and start < previous_end - 0.01:
            overlap_count += 1
        if previous_text and text == previous_text:
            repeated_count += 1
        previous_text = text
        previous_end = max(previous_end, end)
        for word in cue.get("words") or []:
            if not isinstance(word, dict) or word.get("probability") is None:
                continue
            total_confidence_words += 1
            if _number(word.get("probability")) < 0.45:
                low_confidence_words += 1
    low_ratio = low_confidence_words / total_confidence_words if total_confidence_words else 0.0
    warnings = []
    if overlap_count:
        warnings.append("overlapping-cues")
    if fast_count:
        warnings.append("reading-speed")
    if repeated_count:
        warnings.append("adjacent-repetition")
    if low_ratio >= 0.2:
        warnings.append("low-confidence")
    return {
        "cue_count": len(cues),
        "overlap_count": overlap_count,
        "fast_cue_count": fast_count,
        "short_cue_count": short_count,
        "repeated_cue_count": repeated_count,
        "max_chars_per_second": round(max_cps, 2),
        "low_confidence_word_ratio": round(low_ratio, 4),
        "warnings": warnings,
    }


def _fallback_segments(raw_segments: Iterable[object], offset_seconds: float) -> list[dict]:
    out: list[dict] = []
    for item in raw_segments:
        text = clean_subtitle_text(_read_value(item, "text", ""))
        if not text:
            continue
        start = max(0.0, _number(_read_value(item, "start")) + offset_seconds)
        end = max(start + 0.2, _number(_read_value(item, "end"), start + 0.2) + offset_seconds)
        out.append({"start": round(start, 3), "end": round(end, 3), "text": text})
    return out


def regroup_word_segments(
    raw_segments: Iterable[object],
    language: object = "",
    *,
    max_chars: int = 24,
    max_seconds: float = 7.0,
    max_gap: float = 0.8,
    min_seconds: float = 0.8,
    offset_seconds: float = 0.0,
) -> list[dict]:
    """Build readable subtitle cues while preserving word-level timestamps."""
    raw_segments = list(raw_segments)
    words: list[dict] = []
    for segment in raw_segments:
        segment_words = _read_value(segment, "words", []) or []
        for item in segment_words:
            word = _word_from(item, offset_seconds)
            if word is not None:
                words.append(word)
    if not words:
        return _fallback_segments(raw_segments, offset_seconds)

    words.sort(key=lambda item: (item["start"], item["end"]))
    language_code = normalize_language_code(language)
    contains_cjk = language_code in {"zh", "ja", "ko"} or any(
        _CJK_RE.search(str(word.get("word") or "")) for word in words
    )
    char_limit = max(8, int(max_chars))
    if not contains_cjk:
        char_limit = max(32, int(round(char_limit * 1.75)))
    duration_limit = max(1.0, float(max_seconds))
    gap_limit = max(0.1, float(max_gap))

    cues: list[dict] = []
    current: list[dict] = []

    def flush() -> None:
        nonlocal current
        if not current:
            return
        text = _text_for_words(current)
        if text:
            cues.append(
                {
                    "start": round(current[0]["start"], 3),
                    "end": round(max(current[-1]["end"], current[0]["start"] + 0.2), 3),
                    "text": text,
                    "words": [dict(word) for word in current],
                }
            )
        current = []

    for word in words:
        if current and word["start"] - current[-1]["end"] >= gap_limit:
            flush()
        current.append(word)
        text = _text_for_words(current)
        too_long = _visible_length(text) > char_limit
        too_slow = current[-1]["end"] - current[0]["start"] > duration_limit
        if (too_long or too_slow) and len(current) > 1:
            last = current.pop()
            flush()
            current = [last]
            text = _text_for_words(current)
        duration = current[-1]["end"] - current[0]["start"]
        if _SENTENCE_END_RE.search(text) and (duration >= 0.8 or _visible_length(text) >= 4):
            flush()
    flush()
    return _polish_cue_timing(
        cues,
        contains_cjk=contains_cjk,
        min_seconds=min_seconds,
        max_seconds=duration_limit,
    )


def contains_translation(segments: Iterable[dict]) -> bool:
    for item in segments:
        if not isinstance(item, dict):
            continue
        original = clean_subtitle_text(item.get("text"))
        translated = clean_subtitle_text(
            item.get("translation_zh") or item.get("zh") or item.get("translated_text")
        )
        if translated and translated != original:
            return True
    return False

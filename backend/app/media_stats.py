from __future__ import annotations

import csv
import json
import os
import time
from collections import Counter
from pathlib import Path
from .db import get_settings


def media_root() -> Path:
    settings = get_settings()
    return Path(settings.get("media_root") or os.environ.get("MEDIA_ROOT", "/media"))


def output_root() -> Path:
    settings = get_settings()
    return Path(settings.get("output_root") or settings.get("media_root") or os.environ.get("MEDIA_OUTPUT_ROOT") or os.environ.get("MEDIA_ROOT", "/media"))


_SUMMARY_CACHE: tuple[float, dict] | None = None
SUMMARY_TTL_SECONDS = 30


def count_files(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())


def immediate_counts(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for item in sorted([p for p in path.iterdir() if p.is_dir()], key=lambda p: p.name):
        out.append({"name": item.name, "files": count_files(item)})
    return out


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"error": str(exc)}


def applied_status(root: Path) -> dict:
    path = root / "_MANIFESTS" / "applied_moves.csv"
    if not path.exists():
        return {"rows": 0, "status": {}}
    text = path.read_text(encoding="utf-8-sig", errors="replace").replace("\x00", "")
    counts = Counter()
    rows = 0
    for row in csv.DictReader(text.splitlines()):
        rows += 1
        counts[row.get("status", "unknown")] += 1
    return {"rows": rows, "status": dict(counts)}


def applied_rollup(root: Path) -> dict | None:
    path = root / "_MANIFESTS" / "applied_moves.csv"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8-sig", errors="replace").replace("\x00", "")
    status = Counter()
    top = Counter()
    keywords = Counter()
    actors = Counter()
    rows = 0
    for row in csv.DictReader(text.splitlines()):
        rows += 1
        row_status = row.get("status", "unknown")
        status[row_status] += 1
        if row_status not in {"moved", "duplicate"}:
            continue
        new_path = row.get("new_path", "")
        parts = [part for part in new_path.split("/") if part]
        if not parts:
            continue
        if parts[0] == "Actors" and len(parts) > 1:
            top["actors"] += 1
            actors[parts[1]] += 1
        elif parts[:2] == ["_REVIEW", "Keywords"] and len(parts) > 2:
            top["keywords"] += 1
            keywords[parts[2]] += 1
        elif parts[:2] == ["_REVIEW", "UnknownActor"]:
            top["unknown"] += 1
        elif parts[:2] == ["_REVIEW", "Faces"]:
            top["faces"] += 1
        elif parts[:2] == ["_REVIEW", "Duplicates"]:
            top["duplicates"] += 1
        elif parts[:2] == ["_REVIEW", "NeedsManualCheck"]:
            top["needs_manual_check"] += 1
    return {
        "rows": rows,
        "status": dict(status),
        "top": {
            "actors": top["actors"],
            "keywords": top["keywords"],
            "unknown": top["unknown"],
            "faces": top["faces"],
            "duplicates": top["duplicates"],
            "needs_manual_check": top["needs_manual_check"],
        },
        "keywords": [{"name": name, "files": count} for name, count in sorted(keywords.items())],
        "actors_sample": [
            {"name": name, "files": count}
            for name, count in sorted(actors.items(), key=lambda item: (-item[1], item[0]))[:80]
        ],
    }


def csv_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace").replace("\x00", "")
        return max(0, sum(1 for _ in text.splitlines()) - 1)
    except Exception:
        return 0


def jsonl_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            return sum(1 for line in handle if line.strip())
    except Exception:
        return 0


def summary() -> dict:
    global _SUMMARY_CACHE
    now = time.time()
    if _SUMMARY_CACHE and now - _SUMMARY_CACHE[0] < SUMMARY_TTL_SECONDS:
        return _SUMMARY_CACHE[1]
    root = media_root()
    library = output_root()
    manifests = library / "_MANIFESTS"
    state = read_json(manifests / "library_state.json")
    rollup = applied_rollup(library)
    top = state.get("top") or (rollup["top"] if rollup else {
        "actors": 0,
        "keywords": 0,
        "unknown": 0,
        "faces": 0,
        "duplicates": 0,
        "needs_manual_check": 0,
    })
    settings = get_settings()
    source_names = [item.strip().strip("/") for item in (settings.get("source_dirs") or os.environ.get("MEDIA_SOURCE_DIRS", "")).split(",") if item.strip()]
    if not source_names:
        source_names = ["photos", "photos2", "videos", "videos2"]
    source_leftovers = {
        name: len([p for p in (root / name).iterdir() if p.is_file()]) if (root / name).exists() else 0
        for name in source_names
    }
    data = {
        "root": str(root),
        "output_root": str(library),
        "exists": root.exists(),
        "output_exists": library.exists(),
        "top": top,
        "source_leftovers": state.get("source_leftovers") or source_leftovers,
        "keywords": state.get("keywords") or (rollup["keywords"] if rollup else immediate_counts(library / "_REVIEW" / "Keywords")),
        "actors_sample": state.get("actors_sample") or (rollup["actors_sample"] if rollup else immediate_counts(library / "Actors")[:80]),
        "library_state": state,
        "summary_json": read_json(manifests / "summary.json"),
        "applied": {"rows": rollup["rows"], "status": rollup["status"]} if rollup else applied_status(root),
        "vision": {
            "cached_media": len([p for p in (manifests / "vision_cache").iterdir() if p.is_dir()]) if (manifests / "vision_cache").exists() else 0,
            "frame_index_rows": csv_count(manifests / "frame_index.csv"),
            "face_index_rows": csv_count(manifests / "face_index.csv"),
            "face_group_rows": csv_count(manifests / "face_groups.csv"),
            "face_move_plan_rows": csv_count(manifests / "face_move_plan.csv"),
            "face_report_rows": csv_count(manifests / "face_cluster_report.csv"),
            "face_merge_suggestion_rows": csv_count(manifests / "face_merge_suggestions.csv"),
            "vision_label_rows": csv_count(manifests / "vision_labels.csv"),
            "vision_embedding_rows": jsonl_count(manifests / "vision_embeddings.jsonl"),
            "vision_move_plan_rows": csv_count(manifests / "vision_move_plan.csv"),
            "organized_duplicate_rows": csv_count(manifests / "organized_duplicates.csv"),
        },
        "analysis": {
            "filename_analysis_rows": csv_count(manifests / "filename_analysis.csv"),
            "filename_words_rows": csv_count(manifests / "filename_words.csv"),
        },
    }
    _SUMMARY_CACHE = (now, data)
    return data

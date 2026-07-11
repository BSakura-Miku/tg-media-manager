from __future__ import annotations

import csv
import hashlib
import json
import math
import mimetypes
import os
import re
import signal
import shlex
import shutil
import struct
import subprocess
import threading
import time
from collections import defaultdict
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable

from .db import connect, get_settings, init_db

try:
    from PIL import Image
except Exception:
    Image = None


VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm"}
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif"}
SKIP_DIRS = {"_MANIFESTS", "__MACOSX", ".git", "@eaDir"}

PLATFORM_PATTERNS = [
    ("twitter", re.compile(r"(?i)(twitter|x\.com|推特)")),
    ("onlyfans", re.compile(r"(?i)(onlyfans|\bof\b)")),
    ("fc2", re.compile(r"(?i)\bfc2\b")),
    ("telegram", re.compile(r"(?i)(telegram|\btg\b|电报)")),
    ("douyin", re.compile(r"(?i)(douyin|抖音)")),
]

TAG_RULES = [
    ("scene_environment", "室内居家", ["室内", "居家", "卧室", "家中", "房间", "床上"]),
    ("scene_environment", "户外露出", ["户外", "露出", "公园", "街拍", "室外"]),
    ("clothing_style", "JK学生", ["jk", "学生", "校服", "学妹", "水手服"]),
    ("clothing_style", "水手服制服", ["水手服", "制服", "校服"]),
    ("clothing_style", "COS角色", ["cos", "cosplay", "角色扮演", "原神", "碧蓝", "洛丽塔"]),
    ("clothing_style", "黑丝白丝", ["黑丝", "白丝", "丝袜", "长筒袜", "白袜"]),
    ("shooting_method", "自拍露脸", ["自拍", "露脸", "第一视角"]),
    ("shooting_method", "第三视角", ["第三视角", "摄影", "拍摄"]),
    ("content_type", "足交足控", ["足交", "足控", "脚", "美足"]),
    ("content_type", "口交", ["口交", "吹箫", "口活", "含弄", "舔棒", "blowjob", "oral"]),
    ("content_type", "手交", ["手交", "手活", "撸动", "打手枪", "handjob"]),
    ("content_type", "后入", ["后入", "背入", "后背体位", "doggy"]),
    ("content_type", "骑乘", ["骑乘", "女上位", "坐上去", "cowgirl"]),
    ("content_type", "内射中出", ["内射", "中出", "无套内射", "体内射精"]),
    ("content_type", "道具自慰", ["自慰", "自摸", "玩具", "跳蛋", "震动棒", "假阳具", "道具"]),
    ("content_type", "调教捆绑", ["调教", "捆绑", "束缚", "绑缚", "绳缚", "sm"]),
    ("clothing_style", "死库水泳装", ["死库水", "学校泳装", "竞泳", "泳装", "泳衣"]),
    ("quality", "4K", ["4k", "2160p"]),
    ("quality", "1080P", ["1080p", "fhd"]),
    ("quality", "720P", ["720p", "hd"]),
]

RISK_TERMS = ["未成年", "未满", "初中", "小学生", "幼", "萝莉", "1[2-7]岁"]


def output_root() -> Path:
    settings = get_settings()
    return Path(settings.get("output_root") or settings.get("media_root") or os.environ.get("MEDIA_OUTPUT_ROOT") or os.environ.get("MEDIA_ROOT", "/media"))


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8-sig", errors="replace").replace("\x00", "")
    return list(csv.DictReader(StringIO(text)))


def media_type_for(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in VIDEO_EXT:
        return "video"
    if ext in PHOTO_EXT:
        return "photo"
    return "other"


def safe_relative(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def hash8_from_name(value: str) -> str:
    match = re.search(r"(?i)([0-9a-f]{8})(?=\.[^.]+$|$)", Path(value or "").name)
    return match.group(1).lower() if match else ""


def normalized_text(value: str) -> str:
    return re.sub(r"[_\-.()[\]{}【】]+", " ", value).strip()


def first_match(pattern: str, text: str) -> str:
    match = re.search(pattern, text, flags=re.I)
    return match.group(0) if match else ""


def split_tokens(stem: str) -> list[str]:
    text = normalized_text(stem)
    tokens = [part.strip() for part in re.split(r"\s+|,|，|、|\|", text) if part.strip()]
    return [token for token in tokens if len(token) <= 40]


def parse_filename(filename: str, path: Path) -> dict:
    stem = Path(filename).stem
    text = normalized_text(stem)
    lower = text.lower()
    tokens = split_tokens(stem)
    platform = ""
    for name, pattern in PLATFORM_PATTERNS:
        if pattern.search(text):
            platform = name
            break
    date = first_match(r"20\d{2}[-_年.]?\d{1,2}[-_月.]?\d{1,2}", text)
    resolution = first_match(r"(?:[1-9]\d{2,4})[xX×](?:[1-9]\d{2,4})|(?:2160|1440|1080|720)[pP]|4[kK]", text)
    code = first_match(r"\b[A-Z]{2,6}[-_ ]?\d{2,6}\b", text)
    quality = "4K" if re.search(r"(?i)(4k|2160p)", text) else "1080P" if re.search(r"(?i)1080p", text) else "720P" if re.search(r"(?i)720p", text) else ""
    author = ""
    person = ""
    series = ""
    scene = ""
    if len(tokens) >= 2:
        author = tokens[0] if not re.search(r"(?i)^(vid|img|video|photo|telegram|twitter|x|tg)$", tokens[0]) else ""
        person = tokens[1] if author else tokens[0]
    elif tokens:
        person = tokens[0]
    for category, tag, words in TAG_RULES:
        if any(word.lower() in lower for word in words):
            if category == "scene_environment" and not scene:
                scene = tag
            break
    if len(tokens) >= 3:
        series = tokens[2]
    risk_state = "review" if any(re.search(term, text, flags=re.I) for term in RISK_TERMS) else "normal"
    return {
        "author": author[:80],
        "person": person[:80],
        "platform": platform,
        "series": series[:80],
        "code": code,
        "scene": scene,
        "quality": quality or resolution,
        "resolution": resolution,
        "date_text": date,
        "risk_state": risk_state,
    }


def tags_for(filename: str, rel_path: str, parsed: dict) -> list[dict]:
    text = f"{filename} {rel_path}".lower()
    tags: list[dict] = []
    for category, tag, words in TAG_RULES:
        if any(word.lower() in text for word in words):
            confidence = 0.92 if any(word.lower() in Path(filename).stem.lower() for word in words) else 0.78
            state = "confirmed" if confidence >= 0.85 else "pending"
            tags.append({"tag": tag, "category": category, "confidence": confidence, "source": "filename", "state": state})
    if parsed.get("platform"):
        tags.append({"tag": parsed["platform"], "category": "source_platform", "confidence": 0.95, "source": "filename", "state": "confirmed"})
    if parsed.get("quality"):
        tags.append({"tag": parsed["quality"], "category": "quality", "confidence": 0.9, "source": "filename", "state": "confirmed"})
    if parsed.get("risk_state") != "normal":
        tags.append({"tag": "风险待确认", "category": "risk", "confidence": 0.8, "source": "filename", "state": "pending"})
    unique = {}
    for item in tags:
        unique[(item["tag"], item["source"])] = item
    return list(unique.values())


def category_for_tag(tag: str) -> str:
    for category, known_tag, _words in TAG_RULES:
        if known_tag == tag:
            return category
    return "vision"


def manifest_maps(root: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    manifests = root / "_MANIFESTS"
    manifest = {}
    for row in read_csv(manifests / "manifest_all.csv"):
        original = row.get("original_path", "")
        if original:
            manifest[original] = row
    applied = {}
    for row in movement_rows(manifests):
        new_path = row.get("new_path", "")
        if new_path:
            applied[new_path] = row
    return manifest, applied


def movement_rows(manifests: Path) -> list[dict]:
    rows: list[dict] = []
    for row in read_csv(manifests / "applied_moves.csv"):
        if row.get("original_path") and row.get("new_path"):
            rows.append({**row, "source_file": "applied_moves", "original_path": row["original_path"], "new_path": row["new_path"]})
    for filename in ("vision_move_plan.csv", "face_move_plan.csv", "dedupe_move_plan.csv", "organized_duplicates.csv"):
        for row in read_csv(manifests / filename):
            src = row.get("source") or row.get("original_path") or row.get("path") or row.get("media_path")
            dst = row.get("destination") or row.get("new_path") or row.get("duplicate_path")
            if src and dst:
                rows.append({**row, "source_file": filename, "original_path": src, "new_path": dst})
    for row in read_csv(manifests / "move_plan.csv"):
        src = row.get("original_path")
        dst = row.get("planned_path")
        if src and dst:
            rows.append({**row, "source_file": "move_plan", "original_path": src, "new_path": dst})
    return rows


def trace_original_source(root: Path, rel_path: str, hash_value: str = "", hash8: str = "", fallback_name: str = "") -> dict:
    manifests = root / "_MANIFESTS"
    hash8 = (hash8 or hash8_from_name(rel_path) or hash8_from_name(fallback_name)).lower()
    transitions = {}
    row_by_dest = {}
    for row in movement_rows(manifests):
        dst = row.get("new_path", "")
        src = row.get("original_path", "")
        if dst and src and dst not in transitions:
            transitions[dst] = src
            row_by_dest[dst] = row
    current = rel_path
    source_path = ""
    source_name = fallback_name or Path(rel_path).name
    source_kind = "index"
    visited = set()
    for _ in range(16):
        if not current or current in visited or current not in transitions:
            break
        visited.add(current)
        source_path = transitions[current]
        source_name = Path(source_path).name or source_name
        source_kind = str(row_by_dest.get(current, {}).get("source_file") or "move_chain")
        current = source_path
    if not source_path and hash8:
        for row in movement_rows(manifests):
            before = (row.get("hash_before") or row.get("hash") or "").lower()
            if before.startswith(hash8) or hash8_from_name(row.get("new_path", "")) == hash8 or hash8_from_name(row.get("original_path", "")) == hash8:
                source_path = row.get("original_path", "") or source_path
                source_name = Path(source_path).name or source_name
                source_kind = str(row.get("source_file") or "hash8_move_match")
                current = source_path
                break
    for manifest in read_csv(manifests / "manifest_all.csv"):
        original_path = manifest.get("original_path", "")
        manifest_hash = (manifest.get("hash") or "").lower()
        manifest_hash8 = (manifest.get("hash8") or "").lower()
        if (current and original_path == current) or (source_path and original_path == source_path) or (hash_value and manifest.get("hash") == hash_value) or (hash8 and (manifest_hash8 == hash8 or manifest_hash.startswith(hash8))):
            source_path = original_path or source_path
            source_name = manifest.get("original_name") or Path(source_path).name or source_name
            source_kind = "manifest_all"
            break
    return {
        "display_original_name": source_name,
        "source_original_path": source_path,
        "original_name_source": source_kind,
    }


def iter_media_files(root: Path):
    if not root.exists():
        return
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        media_type = media_type_for(path)
        if media_type == "other":
            continue
        yield path, media_type


def infer_author_from_path(root: Path, path: Path) -> str:
    rel = Path(safe_relative(root, path))
    parts = rel.parts
    if len(parts) >= 3 and parts[0] == "Actors":
        return parts[1]
    return ""


def infer_source_from_path(root: Path, path: Path) -> str:
    rel = Path(safe_relative(root, path))
    if not rel.parts:
        return ""
    if rel.parts[0] == "_REVIEW" and len(rel.parts) > 1:
        return "/".join(rel.parts[:3])
    return rel.parts[0]


NORMALIZED_MEDIA_NAME_RE = re.compile(
    r"(?i)^(?:VID|IMG)_\d{8}(?:_\d{6})?(?:_[^.]*)?_[0-9a-f]{8}\.[a-z0-9]+$"
)


def looks_like_normalized_media_name(value: str) -> bool:
    return bool(NORMALIZED_MEDIA_NAME_RE.match(Path(value or "").name))


def upsert_media(conn, root: Path, path: Path, media_type: str, manifest: dict, applied: dict) -> int:
    stat = path.stat()
    rel_path = safe_relative(root, path)
    parsed = parse_filename(path.name, path)
    width = int(float(manifest["width"])) if manifest.get("width") else None
    height = int(float(manifest["height"])) if manifest.get("height") else None
    duration = float(manifest["duration"]) if manifest.get("duration") else None
    existing = conn.execute(
        "SELECT width, height, duration, resolution, original_name, sha256, hash8 FROM media_items WHERE path=?",
        (str(path),),
    ).fetchone()
    preserved_sha256 = str(existing["sha256"] or "") if existing is not None else ""
    preserved_hash8 = str(existing["hash8"] or "") if existing is not None else ""
    sha256 = str(manifest.get("hash") or preserved_sha256)
    hash8 = str(manifest.get("hash8") or preserved_hash8 or sha256[:8])
    original_trace = trace_original_source(root, rel_path, sha256, hash8, path.name)
    traced_original = (
        original_trace.get("display_original_name")
        or manifest.get("original_name")
        or Path(applied.get("original_path", "")).name
        or path.name
    )
    existing_original = str(existing["original_name"] or "") if existing is not None else ""
    if existing_original and not looks_like_normalized_media_name(existing_original):
        original_name = existing_original
    elif existing_original and (not traced_original or looks_like_normalized_media_name(traced_original)):
        original_name = existing_original
    else:
        original_name = traced_original
    if existing is not None:
        width = width if width is not None else existing["width"]
        height = height if height is not None else existing["height"]
        duration = duration if duration is not None else existing["duration"]
    resolution = parsed.get("resolution") or (f"{width}x{height}" if width and height else "") or (existing["resolution"] if existing is not None else "")
    author = infer_author_from_path(root, path) or manifest.get("canonical_actor", "") or parsed.get("author", "")
    source = infer_source_from_path(root, path)
    row = {
        "path": str(path),
        "root": str(root),
        "relative_path": rel_path,
        "filename": path.name,
        "original_name": original_name,
        "ext": path.suffix.lower(),
        "media_type": media_type,
        "size_bytes": stat.st_size,
        "mtime": stat.st_mtime,
        "sha256": sha256,
        "hash8": hash8,
        "width": width,
        "height": height,
        "duration": duration,
        "resolution": resolution,
        "author": author,
        "person": parsed.get("person", ""),
        "platform": parsed.get("platform", ""),
        "series": parsed.get("series", ""),
        "code": parsed.get("code", ""),
        "scene": parsed.get("scene", ""),
        "quality": parsed.get("quality", ""),
        "source": source,
        "normalized_path": rel_path,
        "risk_state": parsed.get("risk_state", "normal"),
    }
    columns = list(row.keys())
    placeholders = ",".join("?" for _ in columns)
    update = ",".join(f"{col}=excluded.{col}" for col in columns if col != "path")
    update += ",updated_at=CURRENT_TIMESTAMP"
    conn.execute(
        f"INSERT INTO media_items ({','.join(columns)}) VALUES ({placeholders}) ON CONFLICT(path) DO UPDATE SET {update}",
        [row[col] for col in columns],
    )
    media_id = int(conn.execute("SELECT id FROM media_items WHERE path=?", (str(path),)).fetchone()["id"])
    conn.execute("DELETE FROM media_tags WHERE media_id=? AND source IN ('filename', 'path')", (media_id,))
    tag_rows = tags_for(path.name, rel_path, parsed)
    if author:
        tag_rows.append({"tag": author, "category": "author", "confidence": 1.0, "source": "path", "state": "confirmed"})
    for item in tag_rows:
        conn.execute(
            """
            INSERT OR REPLACE INTO media_tags (media_id, tag, category, confidence, source, state)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (media_id, item["tag"], item["category"], item["confidence"], item["source"], item["state"]),
        )
    return media_id


ProgressCallback = Callable[[str, int, int, str], None]
CancelCheck = Callable[[], bool]


def rebuild_metadata_index(root: Path | None = None, progress: ProgressCallback | None = None, cancel_check: CancelCheck | None = None) -> dict:
    init_db()
    root = root or output_root()
    manifest_by_original, applied_by_new = manifest_maps(root)
    indexed = 0
    started = time.time()
    entries = list(iter_media_files(root))
    total = len(entries)
    if progress:
        progress("index-metadata", 0, total, "")
    seen_paths: set[str] = set()
    batch_size = 100
    for batch_start in range(0, total, batch_size):
        if cancel_check and cancel_check():
            with connect() as conn:
                conn.execute("INSERT INTO media_operations (operation, detail) VALUES (?, ?)", ("rebuild_metadata_index_cancelled", f"indexed={indexed}/{total} root={root}"))
            return {
                "indexed": indexed,
                "total": total,
                "cancelled": True,
                "root": str(root),
                "elapsed_seconds": round(time.time() - started, 3),
            }
        batch = entries[batch_start:batch_start + batch_size]
        last_rel_path = ""
        with connect() as conn:
            for path, media_type in batch:
                rel_path = safe_relative(root, path)
                applied = applied_by_new.get(rel_path, {})
                manifest = manifest_by_original.get(applied.get("original_path", ""), {})
                upsert_media(conn, root, path, media_type, manifest, applied)
                seen_paths.add(str(path))
                indexed += 1
                last_rel_path = rel_path
        if progress:
            progress("index-metadata", indexed, total, last_rel_path)
    with connect() as conn:
        if seen_paths:
            conn.execute("CREATE TEMP TABLE IF NOT EXISTS scan_seen_paths (path TEXT PRIMARY KEY)")
            conn.execute("DELETE FROM scan_seen_paths")
            conn.executemany("INSERT OR IGNORE INTO scan_seen_paths(path) VALUES (?)", ((path,) for path in seen_paths))
            conn.execute(
                """
                DELETE FROM media_items
                WHERE root=?
                  AND NOT EXISTS (SELECT 1 FROM scan_seen_paths seen WHERE seen.path=media_items.path)
                """,
                (str(root),),
            )
        else:
            conn.execute("DELETE FROM media_items WHERE root=?", (str(root),))
        conn.execute("INSERT INTO media_operations (operation, detail) VALUES (?, ?)", ("rebuild_metadata_index", f"indexed={indexed} root={root}"))
    vision = import_vision_outputs(root, progress=progress, cancel_check=cancel_check)
    if vision.get("cancelled"):
        return {
            "indexed": indexed,
            "total": total,
            "vision": vision,
            "cancelled": True,
            "root": str(root),
            "elapsed_seconds": round(time.time() - started, 3),
        }
    if progress:
        progress("index-metadata", total, total, "")
    return {"indexed": indexed, "total": total, "vision": vision, "root": str(root), "elapsed_seconds": round(time.time() - started, 3)}


def parse_frame_rate(value: str) -> float | None:
    if not value:
        return None
    if "/" in value:
        left, right = value.split("/", 1)
        try:
            denominator = float(right)
            if denominator:
                return round(float(left) / denominator, 4)
        except Exception:
            return None
    try:
        return round(float(value), 4)
    except Exception:
        return None


def probe_photo_metadata(path: Path) -> dict:
    if Image is None:
        return {"probe_status": "failed", "probe_error": "Pillow is not available"}
    with Image.open(path) as image:
        width, height = image.size
        return {
            "width": int(width),
            "height": int(height),
            "duration": None,
            "resolution": f"{int(width)}x{int(height)}",
            "codec": "",
            "frame_rate": None,
            "bit_rate": None,
            "container": (image.format or path.suffix.lstrip(".")).lower(),
            "probe_status": "ok",
            "probe_error": "",
        }


def probe_video_metadata(path: Path, timeout: int = 30) -> dict:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if result.returncode != 0:
        return {"probe_status": "failed", "probe_error": (result.stderr or result.stdout or "ffprobe failed")[-500:]}
    payload = json.loads(result.stdout or "{}")
    video_stream = next((stream for stream in payload.get("streams", []) if stream.get("codec_type") == "video"), {})
    fmt = payload.get("format", {})
    width = int(video_stream.get("width") or 0) or None
    height = int(video_stream.get("height") or 0) or None
    duration_value = fmt.get("duration") or video_stream.get("duration")
    try:
        duration = float(duration_value) if duration_value not in (None, "", "N/A") else None
    except Exception:
        duration = None
    bit_rate_value = fmt.get("bit_rate") or video_stream.get("bit_rate")
    try:
        bit_rate = int(float(bit_rate_value)) if bit_rate_value not in (None, "", "N/A") else None
    except Exception:
        bit_rate = None
    return {
        "width": width,
        "height": height,
        "duration": duration,
        "resolution": f"{width}x{height}" if width and height else "",
        "codec": video_stream.get("codec_name") or "",
        "frame_rate": parse_frame_rate(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate") or ""),
        "bit_rate": bit_rate,
        "container": fmt.get("format_name") or path.suffix.lstrip("."),
        "probe_status": "ok" if width or height or duration else "partial",
        "probe_error": "",
    }


def probe_media_metadata(path: Path, media_type: str) -> dict:
    try:
        if media_type == "photo":
            return probe_photo_metadata(path)
        if media_type == "video":
            return probe_video_metadata(path)
    except subprocess.TimeoutExpired:
        return {"probe_status": "failed", "probe_error": "ffprobe timeout"}
    except Exception as exc:
        return {"probe_status": "failed", "probe_error": str(exc)[:500]}
    return {"probe_status": "skipped", "probe_error": "unsupported media type"}


def sha256_file(path: Path, chunk_size: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def backfill_media_hashes(
    root: Path | None = None,
    limit: int | None = None,
    progress: ProgressCallback | None = None,
    cancel_check: CancelCheck | None = None,
) -> dict:
    """Incrementally fill full SHA256/hash8 for media that do not have both values."""
    init_db()
    root = root or output_root()
    sql = """
        SELECT id, path, sha256, hash8
        FROM media_items
        WHERE root=? AND (sha256='' OR hash8='')
        ORDER BY id
    """
    params: list[object] = [str(root)]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(max(0, int(limit)))
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    total = len(rows)
    processed = updated = failed = 0
    if progress:
        progress("hash-backfill", 0, total, "")
    for row in rows:
        if cancel_check and cancel_check():
            return {"ok": False, "cancelled": True, "processed": processed, "total": total, "updated": updated, "failed": failed, "root": str(root)}
        path = Path(row["path"])
        processed += 1
        try:
            digest = str(row["sha256"] or "") or sha256_file(path)
            short = str(row["hash8"] or "") or digest[:8]
            with connect() as conn:
                conn.execute(
                    "UPDATE media_items SET sha256=?, hash8=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (digest, short, int(row["id"])),
                )
            updated += 1
        except OSError:
            failed += 1
        if progress and (processed == total or processed % 25 == 0):
            progress("hash-backfill", processed, total, safe_relative(root, path))
    return {"ok": failed == 0, "processed": processed, "total": total, "updated": updated, "failed": failed, "root": str(root)}


def backfill_media_metadata(
    root: Path | None = None,
    limit: int | None = None,
    only_missing: bool = True,
    progress: ProgressCallback | None = None,
    cancel_check: CancelCheck | None = None,
) -> dict:
    init_db()
    root = root or output_root()
    params: list[object] = [str(root)]
    where = "root=?"
    if only_missing:
        where += """
            AND (
                width IS NULL
                OR height IS NULL
                OR resolution=''
                OR (media_type='video' AND (duration IS NULL OR duration <= 0))
                OR sha256=''
                OR hash8=''
            )
        """
    sql = f"""
        SELECT id, path, media_type, width, height, duration, resolution, sha256, hash8
        FROM media_items
        WHERE {where}
        ORDER BY id
    """
    if limit:
        sql += " LIMIT ?"
        params.append(int(limit))
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    total = len(rows)
    processed = 0
    updated = 0
    failed = 0
    skipped = 0
    hashed = 0
    hash_failed = 0
    started = time.time()
    if progress:
        progress("metadata-backfill", 0, total, "")
    for row in rows:
        if cancel_check and cancel_check():
            return {
                "ok": False,
                "cancelled": True,
                "processed": processed,
                "total": total,
                "updated": updated,
                "failed": failed,
                "skipped": skipped,
                "root": str(root),
                "elapsed_seconds": round(time.time() - started, 3),
            }
        media_id = int(row["id"])
        path = Path(row["path"])
        media_type = row["media_type"]
        processed += 1
        needs_probe = (
            row["width"] is None
            or row["height"] is None
            or not row["resolution"]
            or (media_type == "video" and (row["duration"] is None or float(row["duration"] or 0) <= 0))
        )
        if not path.exists():
            failed += 1
            meta = {"probe_status": "failed", "probe_error": "file missing"}
        elif needs_probe:
            meta = probe_media_metadata(path, media_type)
            if meta.get("probe_status") in {"ok", "partial"}:
                updated += 1
            elif meta.get("probe_status") == "skipped":
                skipped += 1
            else:
                failed += 1
        else:
            meta = {"probe_status": "unchanged", "probe_error": ""}
        sha256 = str(row["sha256"] or "")
        hash8 = str(row["hash8"] or "")
        if path.exists() and (not sha256 or not hash8):
            try:
                sha256 = sha256 or sha256_file(path)
                hash8 = hash8 or sha256[:8]
                hashed += 1
            except OSError:
                hash_failed += 1
        width = meta.get("width")
        height = meta.get("height")
        duration = meta.get("duration")
        resolution = meta.get("resolution") or (f"{width}x{height}" if width and height else "")
        with connect() as conn:
            if needs_probe:
                conn.execute(
                """
                INSERT INTO media_metadata (
                    media_id, width, height, duration, resolution, codec, frame_rate,
                    bit_rate, container, probe_status, probe_error, probed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(media_id) DO UPDATE SET
                    width=excluded.width,
                    height=excluded.height,
                    duration=excluded.duration,
                    resolution=excluded.resolution,
                    codec=excluded.codec,
                    frame_rate=excluded.frame_rate,
                    bit_rate=excluded.bit_rate,
                    container=excluded.container,
                    probe_status=excluded.probe_status,
                    probe_error=excluded.probe_error,
                    probed_at=CURRENT_TIMESTAMP
                """,
                    (
                    media_id,
                    width,
                    height,
                    duration,
                    resolution,
                    meta.get("codec") or "",
                    meta.get("frame_rate"),
                    meta.get("bit_rate"),
                    meta.get("container") or "",
                    meta.get("probe_status") or "failed",
                    meta.get("probe_error") or "",
                    ),
                )
            if meta.get("probe_status") in {"ok", "partial"}:
                conn.execute(
                    """
                    UPDATE media_items
                    SET width=COALESCE(?, width),
                        height=COALESCE(?, height),
                        duration=COALESCE(?, duration),
                        resolution=CASE WHEN ? != '' THEN ? ELSE resolution END,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                    """,
                    (width, height, duration, resolution, resolution, media_id),
                )
            if sha256 or hash8:
                conn.execute(
                    "UPDATE media_items SET sha256=?, hash8=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (sha256, hash8, media_id),
                )
        if progress and (processed == total or processed % 25 == 0):
            progress("metadata-backfill", processed, total, safe_relative(root, path))
    if progress:
        progress("metadata-backfill", total, total, "")
    return {
        "ok": failed == 0 and hash_failed == 0,
        "processed": processed,
        "total": total,
        "updated": updated,
        "failed": failed,
        "skipped": skipped,
        "hashed": hashed,
        "hash_failed": hash_failed,
        "root": str(root),
        "elapsed_seconds": round(time.time() - started, 3),
    }


def percent(part: int | float, total: int | float) -> int:
    if not total:
        return 0
    return int(round(max(0, min(100, float(part) / float(total) * 100))))


def media_index_diagnostics(root: Path | None = None) -> dict:
    init_db()
    root = root or output_root()
    with connect() as conn:
        totals = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN media_type='video' THEN 1 ELSE 0 END) AS videos,
                SUM(CASE WHEN media_type='photo' THEN 1 ELSE 0 END) AS photos,
                SUM(CASE WHEN media_type NOT IN ('video', 'photo') THEN 1 ELSE 0 END) AS other,
                SUM(CASE WHEN width IS NOT NULL AND height IS NOT NULL THEN 1 ELSE 0 END) AS with_dimensions,
                SUM(CASE WHEN resolution != '' THEN 1 ELSE 0 END) AS with_resolution,
                SUM(CASE WHEN media_type='video' AND duration IS NOT NULL AND duration > 0 THEN 1 ELSE 0 END) AS videos_with_duration
            FROM media_items
            WHERE root=?
            """,
            (str(root),),
        ).fetchone()
        tagged = conn.execute("SELECT COUNT(DISTINCT media_id) AS count FROM media_tags").fetchone()["count"]
        transcripts = conn.execute("SELECT COUNT(DISTINCT media_id) AS count FROM media_transcripts").fetchone()["count"]
        timed_transcripts = 0
        for row in conn.execute("SELECT segments_json FROM media_transcripts"):
            try:
                segments = json.loads(row["segments_json"] or "[]")
            except Exception:
                segments = []
            if timed_transcript_segments(segments):
                timed_transcripts += 1
        faces = conn.execute(
            """
            SELECT COUNT(DISTINCT t.media_id) AS count
            FROM media_tags t
            JOIN media_items m ON m.id=t.media_id
            WHERE m.root=? AND (t.category='face_group' OR t.tag LIKE 'FaceGroup_%') AND t.state != 'rejected'
            """,
            (str(root),),
        ).fetchone()["count"]
        vision_labels = conn.execute("SELECT COUNT(DISTINCT media_id) AS count FROM media_tags WHERE source IN ('vision', 'openclip', 'calibrated-vision') OR category IN ('scene_environment', 'clothing_style', 'shooting_method', 'content_type', 'vision')").fetchone()["count"]
        embeddings = conn.execute("SELECT kind, COUNT(DISTINCT media_id) AS count FROM media_embeddings GROUP BY kind").fetchall()
        failed_jobs = conn.execute(
            """
            SELECT id, command, status, message, stage, failed_count, finished_at, stderr
            FROM jobs
            WHERE status='failed'
            ORDER BY id DESC
            LIMIT 8
            """
        ).fetchall()
        meta_rows = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN probe_status IN ('ok', 'partial') THEN 1 ELSE 0 END) AS ok,
                SUM(CASE WHEN probe_status='failed' THEN 1 ELSE 0 END) AS failed
            FROM media_metadata
            """
        ).fetchone()
    total = int(totals["total"] or 0)
    videos = int(totals["videos"] or 0)
    thumbs_dir = root / "_MANIFESTS" / "media_thumbs_v8"
    thumb_count = sum(1 for _ in thumbs_dir.rglob("*.jpg")) if thumbs_dir.exists() else 0
    subtitles = root / "_MANIFESTS" / "subtitles"
    subtitle_count = sum(1 for _ in subtitles.rglob("*.vtt")) if subtitles.exists() else 0
    face_group_rows = len(read_csv(root / "_MANIFESTS" / "face_groups.csv"))
    try:
        from .thumbnail_tools import thumbnail_health_summary

        thumb_health = thumbnail_health_summary(root, sample_limit=300)
    except Exception as exc:
        thumb_health = {"error": str(exc), "sample_checked": 0, "sample_healthy": 0, "sample_unhealthy": 0, "sample_missing": 0}
    try:
        from .model_manager import model_catalog

        catalog = model_catalog()
        missing_models = [
            {
                "id": model.get("id"),
                "name": model.get("name"),
                "category": model.get("category"),
                "recommended": bool(model.get("recommended")),
                "status": model.get("status"),
            }
            for model in catalog.get("models", [])
            if model.get("status") != "ready"
        ]
    except Exception as exc:
        missing_models = [{"id": "model_catalog", "name": "Model catalog", "category": "system", "status": "error", "error": str(exc)}]
    embedding_counts = {str(row["kind"]): int(row["count"] or 0) for row in embeddings}
    coverage = [
        {
            "id": "dimensions",
            "label": "Dimensions",
            "ready": int(totals["with_dimensions"] or 0),
            "total": total,
            "percent": percent(totals["with_dimensions"] or 0, total),
            "action": "metadata-backfill",
        },
        {
            "id": "duration",
            "label": "Video duration",
            "ready": int(totals["videos_with_duration"] or 0),
            "total": videos,
            "percent": percent(totals["videos_with_duration"] or 0, videos),
            "action": "metadata-backfill",
        },
        {
            "id": "resolution",
            "label": "Resolution",
            "ready": int(totals["with_resolution"] or 0),
            "total": total,
            "percent": percent(totals["with_resolution"] or 0, total),
            "action": "metadata-backfill",
        },
        {
            "id": "tags",
            "label": "Tagged media",
            "ready": int(tagged or 0),
            "total": total,
            "percent": percent(tagged or 0, total),
            "action": "index-vision",
        },
        {
            "id": "transcripts",
            "label": "Video transcripts",
            "ready": int(transcripts or 0),
            "total": videos,
            "percent": percent(transcripts or 0, videos),
            "action": "transcribe",
        },
        {
            "id": "thumbnails",
            "label": "Thumbnails",
            "ready": int(thumb_count),
            "total": total,
            "percent": percent(thumb_count, total),
            "action": "repair-thumbnails",
        },
        {
            "id": "timed_subtitles",
            "label": "Timed subtitles",
            "ready": int(timed_transcripts or 0),
            "total": videos,
            "percent": percent(timed_transcripts or 0, videos),
            "action": "transcribe",
        },
        {
            "id": "vision_labels",
            "label": "Vision labels",
            "ready": int(vision_labels or 0),
            "total": total,
            "percent": percent(vision_labels or 0, total),
            "action": "index-vision",
        },
        {
            "id": "text_vectors",
            "label": "Text vectors",
            "ready": int(embedding_counts.get("text", 0) or embedding_counts.get("bge_text", 0)),
            "total": total,
            "percent": percent(embedding_counts.get("text", 0) or embedding_counts.get("bge_text", 0), total),
            "action": "index-semantic-text",
        },
        {
            "id": "bge_text_vectors",
            "label": "BGE text vectors",
            "ready": int(embedding_counts.get("bge_text", 0)),
            "total": total,
            "percent": percent(embedding_counts.get("bge_text", 0), total),
            "action": "index-semantic-text",
        },
        {
            "id": "subtitle_vectors",
            "label": "Subtitle vectors",
            "ready": int(embedding_counts.get("subtitle", 0)),
            "total": videos,
            "percent": percent(embedding_counts.get("subtitle", 0), videos),
            "action": "index-semantic-text",
        },
        {
            "id": "tag_vectors",
            "label": "Tag vectors",
            "ready": int(embedding_counts.get("tag", 0)),
            "total": total,
            "percent": percent(embedding_counts.get("tag", 0), total),
            "action": "index-semantic-text",
        },
        {
            "id": "image_vectors",
            "label": "Image vectors",
            "ready": int(embedding_counts.get("image", 0)),
            "total": total,
            "percent": percent(embedding_counts.get("image", 0), total),
            "action": "index-semantic-vision",
        },
        {
            "id": "clip_image_vectors",
            "label": "OpenCLIP image vectors",
            "ready": int(embedding_counts.get("clip_image", 0)),
            "total": total,
            "percent": percent(embedding_counts.get("clip_image", 0), total),
            "action": "index-semantic-vision",
        },
    ]
    recommendations = []
    for item in coverage:
        if item["total"] and item["percent"] < 90:
            recommendations.append({
                "level": "warning" if item["percent"] >= 50 else "error",
                "title": f"{item['label']} coverage is {item['percent']}%",
                "detail": f"{item['ready']}/{item['total']} indexed. Run {item['action']} to fill missing data.",
                "command": item["action"],
            })
    return {
        "root": str(root),
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "media": {
            "total": total,
            "videos": videos,
            "photos": int(totals["photos"] or 0),
            "other": int(totals["other"] or 0),
            "faces": int(faces or 0),
            "face_group_rows": int(face_group_rows),
            "metadata_rows": int(meta_rows["total"] or 0),
            "metadata_ok": int(meta_rows["ok"] or 0),
            "metadata_failed": int(meta_rows["failed"] or 0),
            "timed_transcripts": int(timed_transcripts or 0),
            "subtitle_files": int(subtitle_count),
            "vision_labels": int(vision_labels or 0),
        },
        "models": {
            "missing": missing_models,
            "missing_recommended": [item for item in missing_models if item.get("recommended")],
        },
        "embeddings": embedding_counts,
        "recent_failed_jobs": [dict(row) for row in failed_jobs],
        "privacy": {
            "local_only": True,
            "media_root": str(root),
            "database_path": os.environ.get("APP_DB", "/data/tg_media_manager.sqlite3"),
            "model_root": os.environ.get("MODEL_ROOT", "/models"),
            "remote_models_enabled": False,
            "model_downloads_enabled": True,
        },
        "thumbnail_health": thumb_health,
        "coverage": coverage,
        "recommendations": recommendations,
    }


def import_vision_outputs(root: Path | None = None, progress: ProgressCallback | None = None, cancel_check: CancelCheck | None = None) -> dict:
    init_db()
    root = root or output_root()
    manifests = root / "_MANIFESTS"
    labels = read_csv(manifests / "vision_labels.csv")
    frames = read_csv(manifests / "frame_index.csv")
    face_groups = read_csv(manifests / "face_groups.csv")
    label_by_path = {row.get("media_path", ""): row for row in labels if row.get("media_path")}
    imported_tags = 0
    face_group_tags = 0
    desired_face_tags: set[tuple[int, str]] = set()
    timeline_segments = 0
    with connect() as conn:
        media_rows = conn.execute("SELECT id, path, relative_path, media_type FROM media_items WHERE root=?", (str(root),)).fetchall()
    media_by_path: dict[str, dict] = {}
    for row in media_rows:
        item = {"id": int(row["id"]), "media_type": row["media_type"]}
        for key in (str(row["relative_path"] or ""), str(row["path"] or "")):
            if key:
                media_by_path[key] = item
                media_by_path[key.replace("\\", "/")] = item
    total = len(labels) + len(frames) + len(face_groups)
    done = 0
    if progress:
        progress("index-vision", 0, total, "_MANIFESTS/vision_labels.csv")
    batch_size = 500
    for batch_start in range(0, len(labels), batch_size):
        if cancel_check and cancel_check():
            return {"vision_tags": imported_tags, "timeline_segments": timeline_segments, "cancelled": True}
        batch = labels[batch_start:batch_start + batch_size]
        with connect() as conn:
            for row in batch:
                media_path = row.get("media_path", "")
                label = row.get("category", "")
                if not media_path or not label:
                    continue
                media = media_by_path.get(media_path)
                if media is None:
                    continue
                try:
                    confidence = float(row.get("score") or 0)
                except Exception:
                    confidence = 0.0
                state = "confirmed" if confidence >= 0.70 else "pending"
                conn.execute(
                    """
                    INSERT OR REPLACE INTO media_tags (media_id, tag, category, confidence, source, state)
                    VALUES (?, ?, ?, ?, 'vision', ?)
                    """,
                    (media["id"], label, category_for_tag(label), confidence, state),
                )
                imported_tags += 1
        done += len(batch)
        if progress:
            progress("index-vision", done, total, "_MANIFESTS/vision_labels.csv")
    for batch_start in range(0, len(face_groups), batch_size):
        if cancel_check and cancel_check():
            return {"vision_tags": imported_tags, "face_group_tags": face_group_tags, "timeline_segments": timeline_segments, "cancelled": True}
        batch = face_groups[batch_start:batch_start + batch_size]
        with connect() as conn:
            for row in batch:
                group = str(row.get("face_group") or "").strip()
                media_path = str(row.get("media_path") or "").strip()
                if not group or not media_path:
                    continue
                media = media_by_path.get(media_path) or media_by_path.get(media_path.replace("\\", "/"))
                if media is None and Path(media_path).is_absolute():
                    try:
                        media = media_by_path.get(str(Path(media_path).relative_to(root)))
                    except ValueError:
                        media = None
                if media is None:
                    continue
                try:
                    confidence = float(row.get("det_score") or 1.0)
                except (TypeError, ValueError):
                    confidence = 1.0
                conn.execute(
                    """
                    INSERT OR REPLACE INTO media_tags (media_id, tag, category, confidence, source, state)
                    VALUES (?, ?, 'face_group', ?, 'face-cluster', 'confirmed')
                    """,
                    (media["id"], group, max(0.0, min(1.0, confidence))),
                )
                desired_face_tags.add((int(media["id"]), group))
        done += len(batch)
        if progress:
            progress("index-vision", done, total, "_MANIFESTS/face_groups.csv")
    face_group_tags = len(desired_face_tags)
    for batch_start in range(0, len(frames), batch_size):
        if cancel_check and cancel_check():
            return {"vision_tags": imported_tags, "face_group_tags": face_group_tags, "timeline_segments": timeline_segments, "cancelled": True}
        batch = frames[batch_start:batch_start + batch_size]
        with connect() as conn:
            for row in batch:
                media_path = row.get("media_path", "")
                media = media_by_path.get(media_path)
                if media is None:
                    continue
                media_id = int(media["id"])
                conn.execute("DELETE FROM media_timeline_segments WHERE media_id=? AND source='keyframe'", (media_id,))
                frame_paths = [item for item in (row.get("frames") or "").split("|") if item]
                if not frame_paths:
                    continue
                label_row = label_by_path.get(media_path, {})
                label = label_row.get("category") or "关键帧"
                try:
                    confidence = float(label_row.get("score") or 0)
                except Exception:
                    confidence = 0.0
                if media["media_type"] == "video":
                    raw_times = [item for item in (row.get("frame_times") or "").split("|") if item]
                    for idx, frame in enumerate(frame_paths):
                        try:
                            start = float(raw_times[idx]) if idx < len(raw_times) else float(idx * 7)
                        except Exception:
                            start = float(idx * 7)
                        try:
                            next_start = float(raw_times[idx + 1]) if idx + 1 < len(raw_times) else start + 7
                        except Exception:
                            next_start = start + 7
                        end = max(start + 1, next_start)
                        conn.execute(
                            """
                            INSERT INTO media_timeline_segments (media_id, start_seconds, end_seconds, label, confidence, source, representative_frame)
                            VALUES (?, ?, ?, ?, ?, 'keyframe', ?)
                            """,
                            (media_id, start, end, label, confidence, frame),
                        )
                        timeline_segments += 1
        done += len(batch)
        if progress:
            current = batch[-1].get("media_path", "") if batch else "_MANIFESTS/frame_index.csv"
            progress("index-vision", done, total, current)
    with connect() as conn:
        conn.execute("CREATE TEMP TABLE IF NOT EXISTS desired_face_tags (media_id INTEGER, tag TEXT, PRIMARY KEY(media_id, tag))")
        conn.execute("DELETE FROM desired_face_tags")
        conn.executemany("INSERT OR IGNORE INTO desired_face_tags(media_id, tag) VALUES (?, ?)", desired_face_tags)
        conn.execute(
            """
            DELETE FROM media_tags
            WHERE source='face-cluster'
              AND media_id IN (SELECT id FROM media_items WHERE root=?)
              AND NOT EXISTS (
                  SELECT 1 FROM desired_face_tags wanted
                  WHERE wanted.media_id=media_tags.media_id AND wanted.tag=media_tags.tag
              )
            """,
            (str(root),),
        )
        conn.execute("INSERT INTO media_operations (operation, detail) VALUES (?, ?)", ("import_vision_outputs", f"vision_tags={imported_tags} face_group_tags={face_group_tags} timeline_segments={timeline_segments} root={root}"))
    if progress:
        progress("index-vision", total, total, "_MANIFESTS/frame_index.csv")
    return {"vision_tags": imported_tags, "face_group_tags": face_group_tags, "timeline_segments": timeline_segments}


def read_vision_embeddings(root: Path | None = None) -> dict[str, dict]:
    root = root or output_root()
    path = root / "_MANIFESTS" / "vision_embeddings.jsonl"
    embeddings: dict[str, dict] = {}
    if not path.exists():
        return embeddings
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            media_path = str(row.get("media_path") or "")
            embedding = row.get("embedding")
            if media_path and isinstance(embedding, list) and embedding:
                embeddings[media_path] = row
    return embeddings


def import_clip_embeddings(
    root: Path | None = None,
    progress: ProgressCallback | None = None,
    cancel_check: CancelCheck | None = None,
    limit: int | None = None,
    only_missing: bool = True,
) -> dict:
    """Import cached OpenCLIP image vectors without loading or running a vision model."""
    init_db()
    root = root or output_root()
    source = root / "_MANIFESTS" / "vision_embeddings.jsonl"
    if not source.exists():
        return {"ok": False, "error": "vision_embeddings.jsonl not found", "imported": 0, "skipped": 0, "root": str(root)}
    with connect() as conn:
        media_rows = conn.execute("SELECT id, path, relative_path FROM media_items WHERE root=?", (str(root),)).fetchall()
        existing_media = {
            int(row["media_id"])
            for row in conn.execute(
                "SELECT DISTINCT e.media_id FROM media_embeddings e JOIN media_items m ON m.id=e.media_id WHERE m.root=? AND e.kind='clip_image'",
                (str(root),),
            ).fetchall()
        }
    media_by_path: dict[str, int] = {}
    for row in media_rows:
        for key in (str(row["relative_path"] or ""), str(row["path"] or "")):
            if key:
                media_by_path[key] = int(row["id"])
                media_by_path[key.replace("\\", "/")] = int(row["id"])
    with source.open("r", encoding="utf-8", errors="replace") as count_handle:
        total = sum(1 for line in count_handle if line.strip())
    if limit is not None:
        total = min(total, max(0, int(limit)))
    imported = skipped = failed = processed = 0
    if progress:
        progress("index-clip-cache", 0, total, str(source.name))
    with source.open("r", encoding="utf-8", errors="replace") as handle, connect() as conn:
        for line in handle:
            if limit is not None and processed >= max(0, int(limit)):
                break
            if not line.strip():
                continue
            if cancel_check and cancel_check():
                conn.commit()
                return {"ok": False, "cancelled": True, "processed": processed, "total": total, "imported": imported, "skipped": skipped, "failed": failed, "root": str(root)}
            processed += 1
            item: dict = {}
            try:
                item = json.loads(line)
                media_path = str(item.get("media_path") or "")
                media_id = media_by_path.get(media_path) or media_by_path.get(media_path.replace("\\", "/"))
                vector = item.get("embedding")
                if not media_id or not isinstance(vector, list) or not vector:
                    skipped += 1
                    continue
                if only_missing and media_id in existing_media:
                    skipped += 1
                    continue
                values = [float(value) for value in vector]
                norm = math.sqrt(sum(value * value for value in values)) or 1.0
                values = [value / norm for value in values]
                model_name = str(item.get("model") or os.environ.get("OPENCLIP_MODEL", "ViT-L-14"))
                pretrained = str(item.get("pretrained") or os.environ.get("OPENCLIP_PRETRAINED", "laion2b_s32b_b82k"))
                model = f"openclip:{model_name}:{pretrained}"
                conn.execute("DELETE FROM media_embeddings WHERE media_id=? AND kind='clip_image'", (media_id,))
                conn.execute(
                    """
                    INSERT INTO media_embeddings (media_id, kind, model, dim, vector, text, updated_at)
                    VALUES (?, 'clip_image', ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (media_id, model, len(values), pack_vector(values), media_path[:4000]),
                )
                existing_media.add(media_id)
                imported += 1
            except (json.JSONDecodeError, TypeError, ValueError, struct.error):
                failed += 1
            if processed % 250 == 0:
                conn.commit()
                if progress:
                    progress("index-clip-cache", processed, total, str(item.get("media_path") or "") if isinstance(item, dict) else "")
        conn.commit()
        conn.execute(
            "INSERT INTO media_operations (operation, detail) VALUES (?, ?)",
            ("import_clip_embeddings", f"imported={imported} skipped={skipped} failed={failed} source={source}"),
        )
    if progress:
        progress("index-clip-cache", processed, total, str(source.name))
    return {"ok": failed == 0, "processed": processed, "total": total, "imported": imported, "skipped": skipped, "failed": failed, "root": str(root)}


def dot_score(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def mean_vector(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    size = len(vectors[0])
    totals = [0.0] * size
    for vector in vectors:
        for idx, value in enumerate(vector[:size]):
            totals[idx] += float(value)
    mean = [value / len(vectors) for value in totals]
    norm = sum(value * value for value in mean) ** 0.5
    return [value / norm for value in mean] if norm else mean


def calibrated_probability(embedding: list[float], positive: list[float], negative: list[float], bias: float = 0.0) -> float:
    pos = dot_score(embedding, positive)
    neg = dot_score(embedding, negative) if negative else 0.0
    raw = (pos - neg) * 8.0 + bias
    if raw > 60:
        return 1.0
    if raw < -60:
        return 0.0
    return 1.0 / (1.0 + pow(2.718281828, -raw))


def train_vision_calibrators(root: Path | None = None, min_positive: int = 2) -> dict:
    init_db()
    root = root or output_root()
    embeddings = read_vision_embeddings(root)
    if not embeddings:
        return {"ok": False, "error": "vision_embeddings.jsonl not found. Run vision-scan first.", "trained": 0}
    trained = 0
    applied = 0
    skipped: list[dict] = []
    with connect() as conn:
        media_rows = conn.execute("SELECT id, relative_path FROM media_items").fetchall()
        path_by_id = {int(row["id"]): row["relative_path"] for row in media_rows}
        media_id_by_path = {row["relative_path"]: int(row["id"]) for row in media_rows}
        feedback = conn.execute(
            """
            SELECT media_id, tag, category, verdict
            FROM tag_feedback
            ORDER BY updated_at DESC
            """
        ).fetchall()
        grouped: dict[tuple[str, str], dict[str, list[list[float]]]] = defaultdict(lambda: {"positive": [], "negative": []})
        for row in feedback:
            media_path = path_by_id.get(int(row["media_id"]), "")
            embedding_row = embeddings.get(media_path)
            if not embedding_row:
                continue
            vector = [float(value) for value in embedding_row["embedding"]]
            key = (row["tag"], row["category"] or category_for_tag(row["tag"]))
            if int(row["verdict"]) > 0:
                grouped[key]["positive"].append(vector)
            else:
                grouped[key]["negative"].append(vector)
        conn.execute("DELETE FROM media_tags WHERE source='vision-calibrated'")
        for (tag, category), samples in grouped.items():
            positives = samples["positive"]
            negatives = samples["negative"]
            if len(positives) < min_positive:
                skipped.append({"tag": tag, "category": category, "positive": len(positives), "negative": len(negatives)})
                continue
            positive_mean = mean_vector(positives)
            negative_mean = mean_vector(negatives)
            model = {
                "tag": tag,
                "category": category,
                "positive": positive_mean,
                "negative": negative_mean,
                "threshold": 0.62 if negatives else 0.68,
                "version": 1,
            }
            conn.execute(
                """
                INSERT INTO vision_calibrators (tag, category, model_json, positive_count, negative_count, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(tag, category) DO UPDATE SET
                    model_json=excluded.model_json,
                    positive_count=excluded.positive_count,
                    negative_count=excluded.negative_count,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (tag, category, json.dumps(model, ensure_ascii=False), len(positives), len(negatives)),
            )
            trained += 1
            for media_path, embedding_row in embeddings.items():
                media_id = media_id_by_path.get(media_path)
                if not media_id:
                    continue
                vector = [float(value) for value in embedding_row["embedding"]]
                score = calibrated_probability(vector, positive_mean, negative_mean)
                if score < model["threshold"]:
                    continue
                state = "confirmed" if score >= 0.76 else "pending"
                conn.execute(
                    """
                    INSERT OR REPLACE INTO media_tags (media_id, tag, category, confidence, source, state)
                    VALUES (?, ?, ?, ?, 'vision-calibrated', ?)
                    """,
                    (media_id, tag, category, score, state),
                )
                applied += 1
        conn.execute(
            "INSERT INTO media_operations (operation, detail) VALUES (?, ?)",
            ("train_vision_calibrators", f"trained={trained} applied={applied} skipped={len(skipped)} root={root}"),
        )
    return {"ok": True, "trained": trained, "applied_tags": applied, "skipped": skipped[:20], "embedding_rows": len(embeddings)}


def vision_calibrator_status(root: Path | None = None) -> dict:
    init_db()
    root = root or output_root()
    embeddings = read_vision_embeddings(root)
    with connect() as conn:
        feedback = conn.execute(
            """
            SELECT tag, category,
                   SUM(CASE WHEN verdict > 0 THEN 1 ELSE 0 END) AS positive,
                   SUM(CASE WHEN verdict < 0 THEN 1 ELSE 0 END) AS negative
            FROM tag_feedback
            GROUP BY tag, category
            ORDER BY positive DESC, negative DESC, tag
            """
        ).fetchall()
        models = conn.execute(
            "SELECT tag, category, positive_count, negative_count, updated_at FROM vision_calibrators ORDER BY updated_at DESC"
        ).fetchall()
    return {
        "embedding_rows": len(embeddings),
        "feedback": [dict(row) for row in feedback],
        "models": [dict(row) for row in models],
    }


def set_tag_feedback(media_id: int, tag: str, category: str, verdict: int, note: str = "") -> dict:
    init_db()
    tag = tag.strip()
    category = (category or category_for_tag(tag)).strip()
    if not tag:
        raise ValueError("tag is required")
    verdict = 1 if verdict > 0 else -1
    with connect() as conn:
        media = conn.execute("SELECT id FROM media_items WHERE id=?", (media_id,)).fetchone()
        if media is None:
            raise KeyError("media not found")
        conn.execute(
            """
            INSERT INTO tag_feedback (media_id, tag, category, verdict, note, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(media_id, tag, category) DO UPDATE SET
                verdict=excluded.verdict,
                note=excluded.note,
                updated_at=CURRENT_TIMESTAMP
            """,
            (media_id, tag, category, verdict, note.strip()),
        )
        if verdict > 0:
            conn.execute(
                """
                INSERT OR REPLACE INTO media_tags (media_id, tag, category, confidence, source, state)
                VALUES (?, ?, ?, 1.0, 'manual', 'confirmed')
                """,
                (media_id, tag, category),
            )
        else:
            conn.execute("UPDATE media_tags SET state='rejected' WHERE media_id=? AND tag=?", (media_id, tag))
        conn.execute(
            "INSERT INTO media_operations (media_id, operation, detail) VALUES (?, 'tag_feedback', ?)",
            (media_id, f"{tag}={verdict}"),
        )
    return {"ok": True, "media_id": media_id, "tag": tag, "category": category, "verdict": verdict}


def set_media_favorite(media_id: int, favorite: bool) -> dict:
    init_db()
    with connect() as conn:
        media = conn.execute("SELECT id FROM media_items WHERE id=?", (media_id,)).fetchone()
        if media is None:
            raise KeyError("media not found")
        if favorite:
            conn.execute(
                """
                INSERT OR REPLACE INTO media_tags (media_id, tag, category, confidence, source, state)
                VALUES (?, 'Favorite', 'system', 1.0, 'manual', 'confirmed')
                """,
                (media_id,),
            )
        else:
            conn.execute("UPDATE media_tags SET state='rejected' WHERE media_id=? AND tag='Favorite' AND source='manual'", (media_id,))
        conn.execute(
            "INSERT INTO media_operations (media_id, operation, detail) VALUES (?, 'favorite', ?)",
            (media_id, "on" if favorite else "off"),
        )
    return {"ok": True, "media_id": media_id, "favorite": favorite}


def add_manual_media_tag(media_id: int, tag: str, category: str = "") -> dict:
    init_db()
    tag = tag.strip()
    category = (category or category_for_tag(tag)).strip()
    if not tag:
        raise ValueError("tag is required")
    with connect() as conn:
        media = conn.execute("SELECT id FROM media_items WHERE id=?", (media_id,)).fetchone()
        if media is None:
            raise KeyError("media not found")
        conn.execute(
            """
            INSERT OR REPLACE INTO media_tags (media_id, tag, category, confidence, source, state)
            VALUES (?, ?, ?, 1.0, 'manual', 'confirmed')
            """,
            (media_id, tag, category),
        )
        conn.execute(
            "INSERT INTO media_operations (media_id, operation, detail) VALUES (?, 'manual_tag', ?)",
            (media_id, f"{category}:{tag}"),
        )
    return {"ok": True, "media_id": media_id, "tag": tag, "category": category}


def set_manual_author(media_id: int, author: str) -> dict:
    init_db()
    author = author.strip()[:120]
    with connect() as conn:
        media = conn.execute("SELECT id, author FROM media_items WHERE id=?", (media_id,)).fetchone()
        if media is None:
            raise KeyError("media not found")
        conn.execute("UPDATE media_items SET author=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (author, media_id))
        conn.execute("UPDATE media_tags SET state='rejected' WHERE media_id=? AND category='author'", (media_id,))
        if author:
            conn.execute(
                """
                INSERT OR REPLACE INTO media_tags (media_id, tag, category, confidence, source, state)
                VALUES (?, ?, 'author', 1.0, 'manual', 'confirmed')
                """,
                (media_id, author),
            )
        conn.execute(
            "INSERT INTO media_operations (media_id, operation, detail) VALUES (?, 'manual_author', ?)",
            (media_id, author or "(clear)"),
        )
    return {"ok": True, "media_id": media_id, "author": author}


def soft_delete_media(media_id: int) -> dict:
    init_db()
    root = output_root().resolve()
    with connect() as conn:
        row = conn.execute("SELECT * FROM media_items WHERE id=?", (media_id,)).fetchone()
        if row is None:
            raise KeyError("media not found")
        media = dict(row)
    source = Path(media["path"]).resolve()
    try:
        source.relative_to(root)
    except ValueError as exc:
        raise ValueError("media path is outside library root") from exc
    if not source.exists():
        raise FileNotFoundError("media file missing")
    type_dir = "Videos" if media.get("media_type") == "video" else "Photos" if media.get("media_type") == "photo" else "Other"
    target_dir = root / "_REVIEW" / "Deleted" / type_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source.name
    if target.exists():
        target = target_dir / f"{source.stem}_{media_id}{source.suffix}"
    shutil.move(str(source), str(target))
    relative_path = str(target.relative_to(root))
    with connect() as conn:
        conn.execute(
            """
            UPDATE media_items
            SET path=?, relative_path=?, filename=?, normalized_path=?, risk_state='deleted', updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (str(target), relative_path, target.name, relative_path, media_id),
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO media_tags (media_id, tag, category, confidence, source, state)
            VALUES (?, 'Deleted', 'system', 1.0, 'manual', 'confirmed')
            """,
            (media_id,),
        )
        conn.execute(
            "INSERT INTO media_operations (media_id, operation, detail) VALUES (?, 'soft_delete', ?)",
            (media_id, relative_path),
        )
    return {"ok": True, "media_id": media_id, "path": relative_path}


def media_query(
    q: str = "",
    media_type: str = "all",
    tag: str = "",
    author: str = "",
    face_group: str = "",
    favorite: str = "",
    has_subtitles: str = "",
    min_duration: float | None = None,
    max_duration: float | None = None,
    resolution: str = "",
    limit: int = 100,
    offset: int = 0,
    include_risk: bool = False,
    randomize: bool = False,
    random_seed: int = 0,
) -> dict:
    clauses = []
    params: list[object] = []
    if not include_risk:
        clauses.append("m.risk_state='normal'")
    if media_type in {"photo", "video"}:
        clauses.append("m.media_type=?")
        params.append(media_type)
    if author:
        clauses.append("m.author LIKE ?")
        params.append(f"%{author}%")
    if tag:
        tag_terms = [item.strip() for item in tag.replace("，", ",").split(",") if item.strip()]
        for tag_term in tag_terms[:6]:
            clauses.append("EXISTS (SELECT 1 FROM media_tags t WHERE t.media_id=m.id AND t.state != 'rejected' AND t.tag LIKE ?)")
            params.append(f"%{tag_term}%")
    if face_group:
        clauses.append("EXISTS (SELECT 1 FROM media_tags fg WHERE fg.media_id=m.id AND fg.state != 'rejected' AND (fg.tag=? OR fg.tag LIKE ? OR fg.category='face_group' AND fg.tag LIKE ?))")
        params.extend([face_group, f"%{face_group}%", f"%{face_group}%"])
    if favorite in {"1", "true", "yes", "only"}:
        clauses.append("EXISTS (SELECT 1 FROM media_tags fav WHERE fav.media_id=m.id AND fav.tag='Favorite' AND fav.state != 'rejected')")
    elif favorite in {"0", "false", "no", "exclude"}:
        clauses.append("NOT EXISTS (SELECT 1 FROM media_tags fav WHERE fav.media_id=m.id AND fav.tag='Favorite' AND fav.state != 'rejected')")
    if has_subtitles in {"1", "true", "yes", "only"}:
        clauses.append("EXISTS (SELECT 1 FROM media_transcripts tr WHERE tr.media_id=m.id AND tr.text != '')")
    elif has_subtitles in {"0", "false", "no", "missing"}:
        clauses.append("NOT EXISTS (SELECT 1 FROM media_transcripts tr WHERE tr.media_id=m.id AND tr.text != '')")
    if min_duration is not None:
        clauses.append("COALESCE(m.duration, 0) >= ?")
        params.append(float(min_duration))
    if max_duration is not None:
        clauses.append("COALESCE(m.duration, 0) <= ?")
        params.append(float(max_duration))
    if resolution:
        clauses.append("(m.resolution LIKE ? OR m.quality LIKE ?)")
        params.extend([f"%{resolution}%", f"%{resolution}%"])
    if q:
        clauses.append("(m.filename LIKE ? OR m.original_name LIKE ? OR m.author LIKE ? OR m.person LIKE ? OR m.scene LIKE ? OR m.platform LIKE ? OR m.quality LIKE ? OR EXISTS (SELECT 1 FROM media_tags t WHERE t.media_id=m.id AND t.tag LIKE ?) OR EXISTS (SELECT 1 FROM media_transcripts tr WHERE tr.media_id=m.id AND tr.text LIKE ?))")
        like = f"%{q}%"
        params.extend([like, like, like, like, like, like, like, like, like])
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    if randomize:
        seed = abs(int(random_seed or 0)) % 2147483647
        if seed == 0:
            seed = 1103515245
        order = f"(((m.id * 1103515245) + {seed}) % 2147483647), m.id DESC"
    else:
        order = "m.mtime DESC, m.id DESC"
    with connect() as conn:
        total = int(conn.execute(f"SELECT COUNT(*) AS c FROM media_items m {where}", params).fetchone()["c"])
        rows = conn.execute(
            f"""
            SELECT
                m.*,
                GROUP_CONCAT(t.tag, ',') AS tags,
                CASE WHEN EXISTS (
                    SELECT 1
                    FROM media_tags ft
                    WHERE ft.media_id=m.id
                      AND ft.tag='Favorite'
                      AND ft.state != 'rejected'
                ) THEN 1 ELSE 0 END AS favorite
            FROM media_items m
            LEFT JOIN media_tags t ON t.media_id=m.id AND t.state != 'rejected'
            {where}
            GROUP BY m.id
            ORDER BY {order}
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()
    return {"total": total, "limit": limit, "offset": offset, "random_seed": random_seed if randomize else 0, "items": [dict(row) for row in rows]}


TOKEN_RE = re.compile(r"[\w\u3040-\u30ff\u3400-\u9fff]+", re.UNICODE)


def semantic_tokens(text: str) -> list[str]:
    tokens = []
    for token in TOKEN_RE.findall((text or "").lower()):
        token = token.strip("_-")
        if len(token) >= 2:
            tokens.append(token[:48])
    return tokens


def hashed_text_vector(text: str, dim: int = 128) -> list[float]:
    vector = [0.0] * dim
    for token in semantic_tokens(text):
        digest = hashlib.blake2b(token.encode("utf-8", errors="ignore"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[bucket] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def hash_bits_vector(signature: str, dim: int = 64) -> list[float]:
    cleaned = re.sub(r"[^0-9a-fA-F]", "", signature or "")
    if not cleaned:
        return []
    value = int(cleaned[:16].ljust(16, "0"), 16)
    vector = [1.0 if (value >> bit) & 1 else -1.0 for bit in range(min(dim, 64))]
    if len(vector) < dim:
        vector.extend([0.0] * (dim - len(vector)))
    norm = math.sqrt(sum(item * item for item in vector)) or 1.0
    return [item / norm for item in vector]


def pack_vector(vector: list[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector) if vector else b""


def unpack_vector(blob: bytes | memoryview | None, dim: int) -> list[float]:
    if not blob or dim <= 0:
        return []
    raw = bytes(blob)
    expected = dim * 4
    if len(raw) < expected:
        return []
    return list(struct.unpack(f"{dim}f", raw[:expected]))


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    count = min(len(left), len(right))
    return float(sum(left[i] * right[i] for i in range(count)))


NL_NORMALIZE_REPLACEMENTS = {
    "漏出": "露出",
    "室外": "户外",
    "外边": "户外",
    "外面": "户外",
    "屋里": "室内",
    "房里": "室内",
    "宾馆": "酒店",
    "旅馆": "酒店",
    "光脚": "裸足",
    "赤脚": "裸足",
    "美脚": "美足",
    "jk服": "JK制服",
    "jk制服": "JK制服",
    "coser": "COS",
    "角色扮演": "COS",
    "对镜": "镜前自拍",
    "自摄": "自拍",
    "自录": "自拍",
    "口述": "口播",
}


NL_TAG_ALIASES = [
    (
        "JK学生",
        (
            "jk",
            "jk服",
            "jk制服",
            "学生",
            "学妹",
            "校服",
            "校园",
            "学校",
            "教室",
            "课堂",
            "课桌",
            "黑板",
            "同学",
            "百褶裙",
            "白衬衫",
        ),
    ),
    (
        "COS角色",
        (
            "cos",
            "cosplay",
            "coser",
            "角色",
            "扮演",
            "角色扮演",
            "假发",
            "二次元",
            "洛丽塔",
            "lolita",
            "原神",
            "碧蓝",
            "明日方舟",
            "猫娘",
            "兽耳",
            "巫女",
            "女仆",
            "兔女郎",
        ),
    ),
    (
        "自拍露脸",
        (
            "自拍",
            "自摄",
            "自录",
            "露脸",
            "正脸",
            "看镜头",
            "镜前",
            "镜子",
            "对镜",
            "手机拍",
            "第一视角",
            "主观",
            "pov",
        ),
    ),
    (
        "黑丝白丝",
        (
            "黑丝",
            "白丝",
            "灰丝",
            "肉丝",
            "丝袜",
            "裤袜",
            "连裤袜",
            "长筒袜",
            "过膝袜",
            "白袜",
            "黑袜",
            "白色长袜",
            "黑色长袜",
            "白色丝袜",
            "黑色丝袜",
        ),
    ),
    (
        "室内居家",
        (
            "室内",
            "屋里",
            "房里",
            "房间",
            "卧室",
            "床上",
            "沙发",
            "家里",
            "家中",
            "居家",
            "酒店",
            "宾馆",
            "浴室",
            "洗手间",
            "厕所",
            "厨房",
            "客厅",
            "教室",
            "房内",
            "室内拍",
        ),
    ),
    (
        "户外露出",
        (
            "户外",
            "室外",
            "外面",
            "外边",
            "外拍",
            "野外",
            "公园",
            "街拍",
            "街上",
            "车里",
            "车内",
            "地铁",
            "电梯",
            "楼道",
            "楼梯间",
            "公共",
            "公共场所",
            "露出",
            "漏出",
            "野拍",
        ),
    ),
    (
        "足交足控",
        (
            "足控",
            "脚",
            "脚丫",
            "脚趾",
            "脚底",
            "脚心",
            "脚掌",
            "足交",
            "裸足",
            "赤足",
            "赤脚",
            "光脚",
            "美足",
        ),
    ),
    (
        "水手服制服",
        (
            "水手服",
            "制服",
            "校服",
            "jk服",
            "jk制服",
            "衬衫",
            "领带",
            "领结",
            "百褶裙",
            "职业装",
            "护士",
            "女仆",
            "兔女郎",
        ),
    ),
    (
        "口交",
        (
            "口交",
            "吹箫",
            "口活",
            "含弄",
            "舔棒",
            "用嘴",
            "嘴巴服务",
            "嘴上服务",
            "嘴上功夫",
            "口部服务",
            "blowjob",
            "oral",
        ),
    ),
    ("手交", ("手交", "手活", "撸动", "打手枪", "handjob")),
    ("后入", ("后入", "背入", "后背体位", "doggy")),
    ("骑乘", ("骑乘", "女上位", "坐上去", "cowgirl")),
    ("内射中出", ("内射", "中出", "无套内射", "体内射精")),
    ("道具自慰", ("自慰", "自摸", "玩具", "跳蛋", "震动棒", "假阳具", "道具")),
    ("调教捆绑", ("调教", "捆绑", "束缚", "绑缚", "绳缚", "sm")),
    ("死库水泳装", ("死库水", "学校泳装", "竞泳", "泳装", "泳衣")),
    ("有人声", ("有声", "说话", "语音", "声音", "台词", "对白", "口播", "直播")),
    ("剧情对白", ("剧情", "对话", "对白", "台词", "聊天", "老师", "同学")),
    ("自拍口播", ("口播", "直播", "自述", "自拍视频")),
    ("低语耳语", ("低语", "耳语", "小声", "轻声", "气声", "悄悄话")),
    ("甜妹音", ("甜妹", "甜声", "甜美", "可爱声", "软萌")),
    ("成熟声线", ("御姐", "成熟", "姐姐音", "低沉", "成熟声线")),
]


SEARCH_TAG_EXPANSIONS = {
    "JK学生": ("JK学生", "学生制服", "校服", "水手服", "校园", "教室", "课桌", "百褶裙"),
    "COS角色": ("COS角色", "cosplay", "角色扮演", "假发", "二次元", "女仆", "兽耳"),
    "自拍露脸": ("自拍露脸", "正脸", "看镜头", "镜前自拍", "手机拍", "第一视角"),
    "黑丝白丝": ("黑丝白丝", "丝袜", "裤袜", "白袜", "黑袜", "过膝袜"),
    "室内居家": ("室内居家", "房间", "卧室", "床上", "沙发", "酒店", "浴室", "教室"),
    "户外露出": ("户外露出", "户外", "室外", "外拍", "街拍", "公园", "公共场景", "露出"),
    "足交足控": ("足交足控", "裸足", "光脚", "美足", "脚底", "脚趾", "足部特写"),
    "水手服制服": ("水手服制服", "制服", "校服", "JK制服", "衬衫", "领带", "职业装"),
    "口交": ("口交", "吹箫", "口活", "含弄", "舔棒", "口部服务", "blowjob", "oral"),
    "手交": ("手交", "手活", "撸动", "手部刺激", "handjob"),
    "后入": ("后入", "背入", "后背体位", "doggy"),
    "骑乘": ("骑乘", "女上位", "坐姿", "cowgirl"),
    "内射中出": ("内射中出", "内射", "中出", "无套内射", "体内射精"),
    "道具自慰": ("道具自慰", "自慰", "自摸", "玩具", "跳蛋", "震动棒", "假阳具"),
    "调教捆绑": ("调教捆绑", "调教", "捆绑", "束缚", "绑缚", "绳缚"),
    "死库水泳装": ("死库水泳装", "死库水", "学校泳装", "竞泳", "泳装", "泳衣"),
    "有人声": ("有人声", "说话", "语音", "台词", "对白", "声音"),
    "剧情对白": ("剧情对白", "剧情", "对话", "台词", "对白"),
    "自拍口播": ("自拍口播", "口播", "直播", "自述", "自拍视频"),
    "低语耳语": ("低语耳语", "低语", "耳语", "小声", "轻声"),
    "甜妹音": ("甜妹音", "甜美声线", "软萌声线", "可爱声线"),
    "成熟声线": ("成熟声线", "御姐声线", "姐姐音", "低沉声线"),
}


_INTENT_ONTOLOGY_LOCK = threading.Lock()
_INTENT_ONTOLOGY_VECTORS: dict[str, list[float]] = {}


NL_QUERY_EXPANSIONS = {
    "telegram": ("tg", "电报", "telegram"),
    "twitter": ("推特", "twitter", "x.com", "x平台"),
    "douyin": ("抖音", "douyin", "短视频"),
    "onlyfans": ("onlyfans", "only fans"),
    "4K": ("4k", "2160p", "超清", "高码率"),
    "1080P": ("1080p", "fhd", "高清"),
    "720P": ("720p", "hd"),
}


def normalize_nl_search_text(text: str) -> str:
    normalized = text or ""
    for source, target in NL_NORMALIZE_REPLACEMENTS.items():
        normalized = normalized.replace(source, target)
    return normalized


def _unique_ordered(items: list[str] | tuple[str, ...]) -> list[str]:
    return [item for item in dict.fromkeys(str(item).strip() for item in items if str(item).strip())]


def _alias_negative_context(haystack: str, alias: str) -> bool:
    alias_lower = alias.lower()
    start = haystack.find(alias_lower)
    while start >= 0:
        prefix = haystack[max(0, start - 3):start]
        if re.search(r"(不要|别|排除|去掉|不想要|不包含|不要有|不要看|过滤)", prefix):
            return True
        start = haystack.find(alias_lower, start + len(alias_lower))
    return False


def _alias_negative_context_any(alias: str, *texts: str) -> bool:
    return any(_alias_negative_context(text, alias) for text in texts if text)


def intent_tag_terms(tag: str) -> list[str]:
    terms = [tag]
    terms.extend(SEARCH_TAG_EXPANSIONS.get(tag, ()))
    for canonical, aliases in NL_TAG_ALIASES:
        if canonical == tag:
            terms.extend(aliases)
            break
    return _unique_ordered(terms)


def intent_tag_matches(tag: str, data: dict) -> bool:
    haystack = " ".join(
        str(data.get(key) or "")
        for key in ("tags", "filename", "original_name", "relative_path", "author", "person", "scene", "source", "text")
    ).lower()
    return any(term.lower() in haystack for term in intent_tag_terms(tag))


def bge_intent_matches(text: str, excluded: set[str] | None = None) -> list[tuple[str, float]]:
    """Map colloquial queries to the local tag ontology with BGE embeddings."""
    query_vector = bge_text_vector(text)
    if not query_vector:
        return []
    excluded = excluded or set()
    threshold = float(os.environ.get("INTENT_BGE_THRESHOLD", "0.72"))
    ranked: list[tuple[str, float]] = []
    for canonical, _aliases in NL_TAG_ALIASES:
        if canonical in excluded:
            continue
        with _INTENT_ONTOLOGY_LOCK:
            prototype_vector = _INTENT_ONTOLOGY_VECTORS.get(canonical)
        if prototype_vector is None:
            prototype_text = f"{canonical} {' '.join(intent_tag_terms(canonical))}"
            prototype_vector = bge_text_vector(prototype_text)
            if prototype_vector:
                with _INTENT_ONTOLOGY_LOCK:
                    _INTENT_ONTOLOGY_VECTORS[canonical] = prototype_vector
        if not prototype_vector or len(prototype_vector) != len(query_vector):
            continue
        score = cosine_similarity(query_vector, prototype_vector)
        if score >= threshold:
            ranked.append((canonical, score))
    return sorted(ranked, key=lambda item: item[1], reverse=True)[:3]


def understand_search_query(query: str) -> dict:
    text = (query or "").strip()
    normalized_text = normalize_nl_search_text(text)
    haystack = f"{text.lower()} {normalized_text.lower()}"
    parsed = parse_natural_search(text)
    must: list[str] = []
    prefer: list[str] = []
    exclude: list[str] = []
    exclude_terms: list[str] = []
    semantic_terms: list[str] = [text, normalized_text]
    matched_aliases: list[dict] = []
    explicit_tags: list[str] = []

    for canonical, aliases in NL_TAG_ALIASES:
        positive_aliases = []
        negative_aliases = []
        for alias in aliases:
            alias_lower = alias.lower()
            if alias_lower not in haystack:
                continue
            if _alias_negative_context_any(alias, text.lower(), normalized_text.lower()):
                negative_aliases.append(alias)
            else:
                positive_aliases.append(alias)
        if negative_aliases and not positive_aliases:
            exclude.append(canonical)
            matched_aliases.append({"tag": canonical, "aliases": _unique_ordered(negative_aliases), "polarity": "exclude"})
            continue
        if negative_aliases:
            exclude_terms.extend(negative_aliases)
        if positive_aliases:
            prefer.append(canonical)
            explicit_tags.append(canonical)
            semantic_terms.extend(positive_aliases)
            semantic_terms.extend(SEARCH_TAG_EXPANSIONS.get(canonical, ()))
            matched_aliases.append({"tag": canonical, "aliases": _unique_ordered(positive_aliases), "polarity": "prefer"})

    strong_patterns = {
        "scene": r"(必须|一定要|只看|就要|限定).{0,8}(室内|户外|教室|酒店|卧室|公园|街拍)",
        "clothing": r"(必须|一定要|只看|就要|限定).{0,8}(制服|校服|水手服|黑丝|白丝|丝袜|cos|jk)",
        "media": r"(只看|就要|必须).{0,8}(视频|图片|照片)",
    }
    has_alternatives = bool(re.search(r"(?:或者|或是|任意|都可以|随便|\bor\b)", haystack))
    keyword_like_query = len(text) <= 48 and not re.search(r"(?:差不多|类似|相关|可能|大概|随便|推荐)", haystack)
    if any(re.search(pattern, haystack) for pattern in strong_patterns.values()):
        must.extend(prefer)
    elif len(_unique_ordered(explicit_tags)) >= 2 and keyword_like_query and not has_alternatives:
        # A short list such as "白丝 学生 口交" is conventionally an AND query.
        must.extend(explicit_tags)

    inferred_matches = bge_intent_matches(text, excluded=set(prefer) | set(exclude)) if text else []
    for canonical, score in inferred_matches:
        prefer.append(canonical)
        semantic_terms.extend(SEARCH_TAG_EXPANSIONS.get(canonical, ()))
        matched_aliases.append({"tag": canonical, "aliases": [], "polarity": "semantic", "score": round(score, 4)})

    if parsed.get("resolution"):
        semantic_terms.append(str(parsed["resolution"]))
    if parsed.get("has_subtitles"):
        semantic_terms.extend(["字幕", "转写", "台词", "对白"])
    if parsed.get("favorite"):
        semantic_terms.append("收藏")
    for label, aliases in NL_QUERY_EXPANSIONS.items():
        if any(alias.lower() in haystack for alias in aliases):
            semantic_terms.append(label)
            semantic_terms.extend(aliases)

    prefer = _unique_ordered(prefer)
    must = _unique_ordered(must)
    exclude = _unique_ordered(exclude)
    parsed["tag"] = ",".join(prefer)
    semantic_terms.extend(prefer)
    for tag in prefer:
        semantic_terms.extend(SEARCH_TAG_EXPANSIONS.get(tag, ()))
    parsed["semantic_query"] = " ".join(_unique_ordered(semantic_terms))
    parsed["explain"] = [
        item for item in parsed.get("explain", [])
        if not str(item).startswith("标签:")
    ]
    if prefer:
        parsed["explain"].append("偏好标签: " + ",".join(prefer))
    if must:
        parsed["explain"].append("强意图: " + ",".join(must))
    if exclude:
        parsed["explain"].append("排除: " + ",".join(exclude))
    if exclude_terms:
        parsed["explain"].append("排除词: " + ",".join(_unique_ordered(exclude_terms)))

    categories = defaultdict(list)
    for tag in prefer:
        categories[category_for_tag(tag)].append(tag)
    confidence = 0.25
    confidence += min(0.45, len(prefer) * 0.09)
    confidence += 0.12 if parsed.get("media_type") != "all" else 0
    confidence += 0.08 if parsed.get("min_duration") or parsed.get("max_duration") else 0
    confidence += 0.06 if parsed.get("resolution") else 0
    confidence = min(0.95, confidence)
    return {
        "provider": "hybrid-intent-bge-v2" if inferred_matches else "local-ontology-v2",
        "query": text,
        "normalized_query": normalized_text,
        "confidence": round(confidence, 3),
        "parsed": parsed,
        "intent": {
            "must": must,
            "prefer": prefer,
            "exclude": exclude,
            "exclude_terms": _unique_ordered(exclude_terms),
            "categories": {key: _unique_ordered(value) for key, value in categories.items()},
            "semantic_terms": _unique_ordered(semantic_terms)[:80],
            "matched_aliases": matched_aliases,
        },
        "filters": {
            "media_type": parsed.get("media_type") or "all",
            "author": parsed.get("author") or "",
            "face_group": parsed.get("face_group") or "",
            "favorite": parsed.get("favorite") or "",
            "has_subtitles": parsed.get("has_subtitles") or "",
            "min_duration": parsed.get("min_duration"),
            "max_duration": parsed.get("max_duration"),
            "resolution": parsed.get("resolution") or "",
        },
    }


def parse_natural_search(query: str) -> dict:
    text = (query or "").strip()
    normalized_text = normalize_nl_search_text(text)
    lowered = text.lower()
    normalized_lowered = normalized_text.lower()
    haystack = f"{lowered} {normalized_lowered}"
    parsed = {
        "q": text,
        "semantic_query": text,
        "media_type": "all",
        "tag": "",
        "author": "",
        "face_group": "",
        "favorite": "",
        "has_subtitles": "",
        "min_duration": None,
        "max_duration": None,
        "resolution": "",
        "explain": [],
    }
    if re.search(r"(视频|影片|片子|片|video|mp4|mov)", haystack):
        parsed["media_type"] = "video"
        parsed["explain"].append("媒体类型: 视频")
    elif re.search(r"(图片|照片|图|photo|image|jpg|png)", haystack):
        parsed["media_type"] = "photo"
        parsed["explain"].append("媒体类型: 图片")
    if re.search(r"(收藏|喜欢|标星|favorite|fav)", haystack):
        parsed["favorite"] = "true"
        parsed["explain"].append("只看收藏")
    if re.search(r"(有字幕|有转写|字幕|台词|语音|对白|说话|有声)", haystack):
        parsed["has_subtitles"] = "true"
        parsed["explain"].append("需要字幕/转写")
    duration_min = re.search(r"(\d+(?:\.\d+)?)\s*(?:分钟|min|minute).*?(?:以上|大于|超过|\+|起)", haystack)
    duration_max = re.search(r"(\d+(?:\.\d+)?)\s*(?:分钟|min|minute).*?(?:以下|小于|以内)", haystack)
    if duration_min:
        parsed["min_duration"] = float(duration_min.group(1)) * 60
        parsed["explain"].append(f"时长 >= {duration_min.group(1)} 分钟")
    elif re.search(r"(\d+(?:\.\d+)?)\s*(?:秒|sec|second).*?(?:以上|大于|超过|\+|起)", haystack):
        value = re.search(r"(\d+(?:\.\d+)?)\s*(?:秒|sec|second).*?(?:以上|大于|超过|\+|起)", haystack)
        parsed["min_duration"] = float(value.group(1))
        parsed["explain"].append(f"时长 >= {value.group(1)} 秒")
    if duration_max:
        parsed["max_duration"] = float(duration_max.group(1)) * 60
        parsed["explain"].append(f"时长 <= {duration_max.group(1)} 分钟")
    if re.search(r"4k|2160|超清", haystack):
        parsed["resolution"] = "4K"
        parsed["explain"].append("分辨率: 4K")
    elif re.search(r"1080|fhd|高清", haystack):
        parsed["resolution"] = "1080"
        parsed["explain"].append("分辨率: 1080")
    elif re.search(r"720|hd", haystack):
        parsed["resolution"] = "720"
        parsed["explain"].append("分辨率: 720")
    tags = []
    for canonical, aliases in NL_TAG_ALIASES:
        if any(alias.lower() in haystack for alias in aliases):
            tags.append(canonical)
    expansion_terms = []
    if tags:
        parsed["tag"] = ",".join(dict.fromkeys(tags))
        parsed["explain"].append("标签: " + parsed["tag"])
        for tag in dict.fromkeys(tags):
            expansion_terms.extend(SEARCH_TAG_EXPANSIONS.get(tag, ()))
    for label, aliases in NL_QUERY_EXPANSIONS.items():
        if any(alias.lower() in haystack for alias in aliases):
            expansion_terms.append(label)
            expansion_terms.extend(aliases)
    semantic_parts = [text, normalized_text, parsed["tag"], *tags, *expansion_terms]
    parsed["semantic_query"] = " ".join(part for part in dict.fromkeys(semantic_parts) if part).strip()
    author_match = re.search(r"(?:作者|人物|演员|creator|author)[:： ]+([\w\u3040-\u30ff\u3400-\u9fff.-]{2,40})", text, re.I)
    if author_match:
        parsed["author"] = author_match.group(1)
        parsed["explain"].append("作者/人物: " + parsed["author"])
    return parsed


def semantic_match_reasons(data: dict, query: str, score: float, kind: str) -> list[str]:
    reasons = []
    if score:
        reasons.append(f"{kind} {score:.2f}")
    tags = str(data.get("tags") or "")
    for token in semantic_tokens(query)[:8]:
        if token and token in tags.lower():
            reasons.append(f"标签命中: {token}")
            break
    filename = str(data.get("filename") or data.get("original_name") or "").lower()
    for token in semantic_tokens(query)[:8]:
        if token and token in filename:
            reasons.append(f"文件名命中: {token}")
            break
    if kind in {"subtitle", "bge_text", "text"} and data.get("kind") == "subtitle":
        reasons.append("字幕/转写相似")
    return reasons[:4]


def media_semantic_text(row: dict, tags: list[str], transcript: str = "") -> str:
    parts = [
        row.get("filename") or "",
        row.get("original_name") or "",
        row.get("author") or "",
        row.get("person") or "",
        row.get("platform") or "",
        row.get("series") or "",
        row.get("scene") or "",
        row.get("quality") or "",
        row.get("resolution") or "",
        " ".join(tags),
        transcript or "",
    ]
    return " ".join(part for part in parts if part)


def model_file_exists(model_id: str) -> bool:
    try:
        from .model_manager import MODEL_REGISTRY

        item = MODEL_REGISTRY.get(model_id) or {}
        relative = item.get("path")
        if not relative:
            return False
        return (Path(os.environ.get("MODEL_ROOT", "/models")) / str(relative)).exists()
    except Exception:
        return False


_SEMANTIC_BACKEND_LOCK = threading.Lock()
_BGE_BACKEND: dict | None = None
_BGE_BACKEND_KEY: tuple[str, str] | None = None
_OPENCLIP_TEXT_BACKEND: dict | None = None
_OPENCLIP_TEXT_BACKEND_KEY: tuple[str, str, str] | None = None


def _registry_model_path(model_id: str) -> Path | None:
    try:
        from .model_manager import MODEL_REGISTRY

        relative = (MODEL_REGISTRY.get(model_id) or {}).get("path")
        return Path(os.environ.get("MODEL_ROOT", "/models")) / str(relative) if relative else None
    except Exception:
        return None


def bge_asset_paths() -> tuple[Path | None, Path | None]:
    explicit_model = os.environ.get("BGE_MODEL_PATH", "").strip()
    registered = Path(explicit_model) if explicit_model else _registry_model_path("bge-small-text")
    if registered is None:
        return None, None
    model_path = registered
    asset_root = registered.parent
    if registered.suffix.lower() != ".onnx":
        asset_root = registered
        model_path = registered / "onnx" / "model_quantized.onnx"
        if not model_path.exists():
            model_path = registered / "model.onnx"
    explicit_tokenizer = os.environ.get("BGE_TOKENIZER_PATH", "").strip()
    tokenizer_path = Path(explicit_tokenizer) if explicit_tokenizer else asset_root / "tokenizer.json"
    if not tokenizer_path.exists() and model_path.parent.parent != model_path.parent:
        parent_candidate = model_path.parent.parent / "tokenizer.json"
        if parent_candidate.exists():
            tokenizer_path = parent_candidate
    return model_path, tokenizer_path


def _load_bge_backend() -> dict | None:
    global _BGE_BACKEND, _BGE_BACKEND_KEY
    model_path, tokenizer_path = bge_asset_paths()
    if model_path is None or tokenizer_path is None:
        return None
    key = (str(model_path), str(tokenizer_path))
    if _BGE_BACKEND is not None and _BGE_BACKEND_KEY == key:
        return _BGE_BACKEND
    if not model_path.is_file() or not tokenizer_path.is_file():
        return None
    with _SEMANTIC_BACKEND_LOCK:
        if _BGE_BACKEND is not None and _BGE_BACKEND_KEY == key:
            return _BGE_BACKEND
        try:
            import numpy as np  # type: ignore
            import onnxruntime as ort  # type: ignore
            from tokenizers import Tokenizer  # type: ignore

            available = ort.get_available_providers()
            providers = [name for name in ("OpenVINOExecutionProvider", "CPUExecutionProvider") if name in available]
            session = ort.InferenceSession(str(model_path), providers=providers or available)
            tokenizer = Tokenizer.from_file(str(tokenizer_path))
            backend = {
                "session": session,
                "tokenizer": tokenizer,
                "numpy": np,
                "model": "bge-small-zh-v1.5-onnx",
                "max_length": max(8, int(os.environ.get("BGE_MAX_LENGTH", "512"))),
            }
            _BGE_BACKEND = backend
            _BGE_BACKEND_KEY = key
            return backend
        except Exception:
            return None


def bge_text_vector(text: str) -> list[float]:
    backend = _load_bge_backend()
    if backend is None or not text.strip():
        return []
    try:
        np = backend["numpy"]
        encoding = backend["tokenizer"].encode(text[:12000])
        max_length = int(backend["max_length"])
        ids = list(encoding.ids[:max_length])
        attention = list(encoding.attention_mask[:max_length])
        type_ids = list(encoding.type_ids[:max_length])
        if not ids:
            return []
        input_names = {item.name for item in backend["session"].get_inputs()}
        feed = {}
        if "input_ids" in input_names:
            feed["input_ids"] = np.asarray([ids], dtype=np.int64)
        if "attention_mask" in input_names:
            feed["attention_mask"] = np.asarray([attention], dtype=np.int64)
        if "token_type_ids" in input_names:
            feed["token_type_ids"] = np.asarray([type_ids], dtype=np.int64)
        outputs = backend["session"].run(None, feed)
        values = np.asarray(outputs[0], dtype=np.float32)
        if values.ndim == 3:
            # BGE v1.5 is trained and published with CLS pooling.
            values = values[:, 0, :]
        if values.ndim == 2:
            values = values[0]
        values = values.reshape(-1)
        norm = float(np.linalg.norm(values)) or 1.0
        return [float(value) for value in values / norm]
    except Exception:
        return []


def _load_openclip_text_backend() -> dict | None:
    global _OPENCLIP_TEXT_BACKEND, _OPENCLIP_TEXT_BACKEND_KEY
    model_name = os.environ.get("OPENCLIP_MODEL", "ViT-L-14")
    pretrained = os.environ.get("OPENCLIP_PRETRAINED", "laion2b_s32b_b82k")
    device = os.environ.get("OPENCLIP_TEXT_DEVICE", "cpu")
    key = (model_name, pretrained, device)
    if _OPENCLIP_TEXT_BACKEND is not None and _OPENCLIP_TEXT_BACKEND_KEY == key:
        return _OPENCLIP_TEXT_BACKEND
    with _SEMANTIC_BACKEND_LOCK:
        if _OPENCLIP_TEXT_BACKEND is not None and _OPENCLIP_TEXT_BACKEND_KEY == key:
            return _OPENCLIP_TEXT_BACKEND
        try:
            import open_clip  # type: ignore
            import torch  # type: ignore

            model, _, _ = open_clip.create_model_and_transforms(model_name, pretrained=pretrained, device=device)
            model.eval()
            backend = {
                "torch": torch,
                "model_instance": model,
                "tokenizer": open_clip.get_tokenizer(model_name),
                "device": device,
                "model": f"openclip:{model_name}:{pretrained}",
            }
            _OPENCLIP_TEXT_BACKEND = backend
            _OPENCLIP_TEXT_BACKEND_KEY = key
            return backend
        except Exception:
            return None


def openclip_text_vector(text: str) -> tuple[list[float], str]:
    backend = _load_openclip_text_backend()
    if backend is None or not text.strip():
        return [], ""
    try:
        torch = backend["torch"]
        tokens = backend["tokenizer"]([text]).to(backend["device"])
        with torch.no_grad():
            features = backend["model_instance"].encode_text(tokens)
            features /= features.norm(dim=-1, keepdim=True)
        return [float(value) for value in features[0].detach().cpu().tolist()], str(backend["model"])
    except Exception:
        return [], ""


def text_embedding(text: str) -> tuple[list[float], str, str]:
    vector = bge_text_vector(text)
    if vector:
        backend = _load_bge_backend() or {}
        return vector, "bge_text", str(backend.get("model") or "bge-small-zh-v1.5-onnx")
    return hashed_text_vector(text), "text", "local-hash-128"


def embedding_kind_for_text() -> tuple[str, str]:
    backend = _load_bge_backend()
    if backend is not None:
        return "bge_text", str(backend.get("model") or "bge-small-zh-v1.5-onnx")
    return "text", "local-hash-128"


def semantic_query_vector(query: str, preferred_kind: str = "") -> tuple[list[float], str]:
    if preferred_kind in {"text", "subtitle", "tag"}:
        return hashed_text_vector(query), "local-hash-128"
    vector, _kind, model = text_embedding(query)
    return vector, model


def visual_signature_for_media(root: Path, row: dict, conn) -> str:
    path = Path(row.get("path") or "")
    if row.get("media_type") == "photo" and path.exists():
        return dhash(path)
    if row.get("media_type") == "video":
        frames = conn.execute(
            """
            SELECT representative_frame
            FROM media_timeline_segments
            WHERE media_id=? AND representative_frame != ''
            ORDER BY start_seconds
            LIMIT 3
            """,
            (row["id"],),
        ).fetchall()
        signatures = []
        for frame in frames:
            sig = dhash(root / frame["representative_frame"])
            if sig:
                signatures.append(sig)
        if signatures:
            return "".join(signatures)
    return ""


def clip_embedding_record_for_media(root: Path, row: dict, vision_embeddings: dict[str, dict]) -> tuple[list[float], str]:
    candidates = [
        str(row.get("relative_path") or ""),
        str(row.get("path") or ""),
        str(Path(row.get("path") or "").relative_to(root)) if str(row.get("path") or "").startswith(str(root)) else "",
    ]
    for key in candidates:
        if not key:
            continue
        item = vision_embeddings.get(key) or vision_embeddings.get(key.replace("\\", "/"))
        if not item:
            continue
        vector = item.get("embedding")
        if isinstance(vector, list) and vector:
            try:
                values = [float(value) for value in vector]
            except (TypeError, ValueError):
                return [], ""
            norm = math.sqrt(sum(value * value for value in values)) or 1.0
            model_name = str(item.get("model") or os.environ.get("OPENCLIP_MODEL", "ViT-L-14"))
            pretrained = str(item.get("pretrained") or os.environ.get("OPENCLIP_PRETRAINED", "laion2b_s32b_b82k"))
            return [value / norm for value in values], f"openclip:{model_name}:{pretrained}"
    return [], ""


def clip_embedding_for_media(root: Path, row: dict, vision_embeddings: dict[str, dict]) -> list[float]:
    return clip_embedding_record_for_media(root, row, vision_embeddings)[0]


def rebuild_semantic_index(
    root: Path | None = None,
    progress: Callable[[str, int, int, str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
    limit: int | None = None,
    mode: str = "all",
) -> dict:
    init_db()
    root = root or output_root()
    processed = 0
    text_count = 0
    visual_count = 0
    clip_count = 0
    cancelled = False
    mode = mode if mode in {"all", "text", "vision"} else "all"
    text_kind, text_model = embedding_kind_for_text()
    clip_import = {"imported": 0, "skipped": 0}
    if mode in {"all", "vision"}:
        clip_import = import_clip_embeddings(root, progress=progress, cancel_check=cancel_check, limit=limit, only_missing=True)
        if clip_import.get("cancelled"):
            return {"ok": False, "cancelled": True, "processed": 0, "text": 0, "visual": 0, "clip": int(clip_import.get("imported") or 0), "mode": mode, "root": str(root)}
        clip_count = int(clip_import.get("imported") or 0)
    with connect() as conn:
        rows = [dict(row) for row in conn.execute("SELECT * FROM media_items ORDER BY id").fetchall()]
        if limit:
            rows = rows[:limit]
        total = len(rows)
        if progress:
            progress(f"index-semantic-{mode}", 0, total, "semantic index")
        for row in rows:
            if cancel_check and cancel_check():
                cancelled = True
                break
            tags = [str(item["tag"]) for item in conn.execute("SELECT tag FROM media_tags WHERE media_id=? AND state != 'rejected'", (row["id"],)).fetchall()]
            if mode in {"all", "text"}:
                transcript_row = conn.execute("SELECT text FROM media_transcripts WHERE media_id=?", (row["id"],)).fetchone()
                transcript = str(transcript_row["text"] or "") if transcript_row else ""
                text = media_semantic_text(row, tags, transcript)
                if text.strip():
                    vector, row_text_kind, row_text_model = text_embedding(text)
                    conn.execute("DELETE FROM media_embeddings WHERE media_id=? AND kind IN ('text', 'bge_text')", (row["id"],))
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO media_embeddings (media_id, kind, model, dim, vector, text, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """,
                        (row["id"], row_text_kind, row_text_model, len(vector), pack_vector(vector), text[:4000]),
                    )
                    text_kind, text_model = row_text_kind, row_text_model
                    text_count += 1
                if tags:
                    tag_text = " ".join(tags)
                    vector = hashed_text_vector(tag_text)
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO media_embeddings (media_id, kind, model, dim, vector, text, updated_at)
                        VALUES (?, 'tag', 'local-hash-128', ?, ?, ?, CURRENT_TIMESTAMP)
                        """,
                        (row["id"], len(vector), pack_vector(vector), tag_text[:4000]),
                    )
                if transcript.strip():
                    vector = hashed_text_vector(transcript)
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO media_embeddings (media_id, kind, model, dim, vector, text, updated_at)
                        VALUES (?, 'subtitle', 'local-hash-128', ?, ?, ?, CURRENT_TIMESTAMP)
                        """,
                        (row["id"], len(vector), pack_vector(vector), transcript[:4000]),
                    )
            if mode in {"all", "vision"}:
                visual_sig = visual_signature_for_media(root, row, conn)
                visual_vector = hash_bits_vector(visual_sig)
                if visual_vector:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO media_embeddings (media_id, kind, model, dim, vector, text, updated_at)
                        VALUES (?, 'image', 'dhash-64', ?, ?, ?, CURRENT_TIMESTAMP)
                        """,
                        (row["id"], len(visual_vector), pack_vector(visual_vector), visual_sig[:256]),
                    )
                    visual_count += 1
            processed += 1
            if processed % 100 == 0:
                conn.commit()
                if progress:
                    progress(f"index-semantic-{mode}", processed, total, row.get("relative_path") or row.get("filename") or "")
        conn.commit()
        try:
            conn.execute(
                "INSERT INTO media_operations (operation, detail) VALUES (?, ?)",
                ("rebuild_semantic_index", f"mode={mode} text={text_count} visual={visual_count} clip={clip_count} processed={processed} root={root}"),
            )
        except Exception:
            # The index is already committed; an audit-log lock should not turn a
            # completed semantic index into a failed job.
            pass
    if progress:
        progress(f"index-semantic-{mode}", processed, total if not cancelled else max(total, processed), "semantic index cancelled" if cancelled else "semantic index complete")
    return {"ok": not cancelled, "cancelled": cancelled, "processed": processed, "text": text_count, "visual": visual_count, "clip": clip_count, "clip_import": clip_import, "mode": mode, "text_model": text_model, "root": str(root)}


def semantic_media_search(
    q: str,
    media_type: str = "all",
    tag: str = "",
    author: str = "",
    face_group: str = "",
    favorite: str = "",
    has_subtitles: str = "",
    min_duration: float | None = None,
    max_duration: float | None = None,
    resolution: str = "",
    limit: int = 80,
    intent: dict | None = None,
    _relax_must_on_empty: bool = True,
) -> dict:
    query = q.strip()
    if not query:
        return media_query(limit=limit)
    hash_query_vector = hashed_text_vector(query)
    bge_query_vector = bge_text_vector(query)
    clip_query_vector, clip_query_model = openclip_text_vector(query)
    rows_out = []
    clauses = ["m.risk_state='normal'"]
    params: list[object] = []
    if media_type in {"photo", "video"}:
        clauses.append("m.media_type=?")
        params.append(media_type)
    if author:
        clauses.append("m.author LIKE ?")
        params.append(f"%{author}%")
    if tag:
        for tag_term in [item.strip() for item in tag.replace("，", ",").split(",") if item.strip()][:6]:
            clauses.append("EXISTS (SELECT 1 FROM media_tags tf WHERE tf.media_id=m.id AND tf.state != 'rejected' AND tf.tag LIKE ?)")
            params.append(f"%{tag_term}%")
    if face_group:
        clauses.append("EXISTS (SELECT 1 FROM media_tags fg WHERE fg.media_id=m.id AND fg.state != 'rejected' AND (fg.tag=? OR fg.tag LIKE ? OR fg.category='face_group' AND fg.tag LIKE ?))")
        params.extend([face_group, f"%{face_group}%", f"%{face_group}%"])
    if favorite in {"1", "true", "yes", "only"}:
        clauses.append("EXISTS (SELECT 1 FROM media_tags fav WHERE fav.media_id=m.id AND fav.tag='Favorite' AND fav.state != 'rejected')")
    elif favorite in {"0", "false", "no", "exclude"}:
        clauses.append("NOT EXISTS (SELECT 1 FROM media_tags fav WHERE fav.media_id=m.id AND fav.tag='Favorite' AND fav.state != 'rejected')")
    if has_subtitles in {"1", "true", "yes", "only"}:
        clauses.append("EXISTS (SELECT 1 FROM media_transcripts tr WHERE tr.media_id=m.id AND tr.text != '')")
    elif has_subtitles in {"0", "false", "no", "missing"}:
        clauses.append("NOT EXISTS (SELECT 1 FROM media_transcripts tr WHERE tr.media_id=m.id AND tr.text != '')")
    if min_duration is not None:
        clauses.append("COALESCE(m.duration, 0) >= ?")
        params.append(float(min_duration))
    if max_duration is not None:
        clauses.append("COALESCE(m.duration, 0) <= ?")
        params.append(float(max_duration))
    if resolution:
        clauses.append("(m.resolution LIKE ? OR m.quality LIKE ?)")
        params.extend([f"%{resolution}%", f"%{resolution}%"])
    where = f"WHERE {' AND '.join(clauses)}"
    with connect() as conn:
        candidate_limit = max(limit, min(50000, int(os.environ.get("SEMANTIC_SEARCH_CANDIDATE_LIMIT", "20000"))))
        cursor = conn.execute(
            f"""
            WITH candidates AS (
                SELECT m.id
                FROM media_items m
                {where}
                ORDER BY m.id DESC
                LIMIT ?
            )
            SELECT e.media_id, e.kind, e.model, e.dim, e.vector, m.*,
                   (SELECT GROUP_CONCAT(t.tag, ',') FROM media_tags t WHERE t.media_id=m.id AND t.state != 'rejected') AS tags
            FROM candidates c
            JOIN media_items m ON m.id=c.id
            JOIN media_embeddings e ON e.media_id=m.id
            WHERE e.kind IN ('text', 'subtitle', 'tag', 'bge_text', 'clip_image')
            ORDER BY m.id DESC, e.kind
            """,
            [*params, candidate_limit],
        )
        scores: dict[int, tuple[float, dict, list[str]]] = {}
        weights = {"bge_text": 1.15, "text": 1.0, "subtitle": 0.9, "tag": 1.05, "clip_image": 1.1}
        preferred_tags = [str(item).strip() for item in ((intent or {}).get("prefer") or []) if str(item).strip()]
        must_tags = [str(item).strip() for item in ((intent or {}).get("must") or []) if str(item).strip()]
        excluded_tags = [str(item).strip() for item in ((intent or {}).get("exclude") or []) if str(item).strip()]
        excluded_terms = [str(item).strip().lower() for item in ((intent or {}).get("exclude_terms") or []) if str(item).strip()]
        while True:
            batch = cursor.fetchmany(500)
            if not batch:
                break
            for row in batch:
                data = dict(row)
                kind = str(data.get("kind") or "")
                item_tags = [part.strip() for part in str(data.get("tags") or "").split(",") if part.strip()]
                if excluded_tags and any(any(excluded.lower() in item.lower() for item in item_tags) for excluded in excluded_tags):
                    continue
                item_search_text = " ".join([
                    str(data.get("filename") or ""),
                    str(data.get("original_name") or ""),
                    str(data.get("relative_path") or ""),
                    str(data.get("author") or ""),
                    str(data.get("person") or ""),
                    str(data.get("scene") or ""),
                    str(data.get("tags") or ""),
                    str(data.get("text") or ""),
                ]).lower()
                if excluded_terms and any(term in item_search_text for term in excluded_terms):
                    continue
                vector = unpack_vector(data.pop("vector", None), int(data.get("dim") or 0))
                if kind == "bge_text":
                    query_vector = bge_query_vector
                elif kind == "clip_image":
                    query_vector = clip_query_vector if clip_query_vector and (not clip_query_model or data.get("model") in {clip_query_model, "openclip-local"}) else []
                else:
                    query_vector = hash_query_vector
                if not query_vector or len(query_vector) != len(vector):
                    continue
                score = cosine_similarity(query_vector, vector) * weights.get(kind, 1.0)
                preferred_hits = [tag_name for tag_name in preferred_tags if intent_tag_matches(tag_name, data)]
                must_hits = [tag_name for tag_name in must_tags if intent_tag_matches(tag_name, data)]
                if must_tags and len(must_hits) != len(must_tags):
                    continue
                if preferred_hits:
                    score += min(0.28, 0.07 * len(preferred_hits))
                if must_hits:
                    score += min(0.36, 0.12 * len(must_hits))
                if tag:
                    score += 0.08
                if author:
                    score += 0.05
                media_id = int(data["media_id"])
                reasons = semantic_match_reasons(data, query, score, kind)
                if preferred_hits:
                    reasons.append("AI意图命中: " + ",".join(preferred_hits[:3]))
                if must_hits:
                    reasons.append("强意图命中: " + ",".join(must_hits[:3]))
                if score > scores.get(media_id, (-2.0, {}, []))[0]:
                    scores[media_id] = (score, data, reasons[:5])
        for score, data, reasons in sorted(scores.values(), key=lambda item: item[0], reverse=True)[:limit]:
            data["semantic_score"] = round(score, 6)
            data["match_reasons"] = reasons
            rows_out.append(data)
    if not rows_out and must_tags and _relax_must_on_empty:
        relaxed_intent = dict(intent or {})
        relaxed_intent["must"] = []
        relaxed = semantic_media_search(
            q=query,
            media_type=media_type,
            tag=tag,
            author=author,
            face_group=face_group,
            favorite=favorite,
            has_subtitles=has_subtitles,
            min_duration=min_duration,
            max_duration=max_duration,
            resolution=resolution,
            limit=limit,
            intent=relaxed_intent,
            _relax_must_on_empty=False,
        )
        relaxed["relaxed_must"] = must_tags
        return relaxed
    if not rows_out:
        return media_query(q=query, media_type=media_type, tag=tag, author=author, face_group=face_group, favorite=favorite, has_subtitles=has_subtitles, min_duration=min_duration, max_duration=max_duration, resolution=resolution, limit=limit)
    return {"total": len(rows_out), "limit": limit, "offset": 0, "semantic": True, "query": query, "understanding": intent or {}, "items": rows_out}


def similar_media(media_id: int, limit: int = 40) -> dict:
    with connect() as conn:
        base = conn.execute("SELECT kind, model, dim, vector FROM media_embeddings WHERE media_id=? ORDER BY CASE kind WHEN 'image' THEN 0 WHEN 'text' THEN 1 ELSE 2 END", (media_id,)).fetchall()
        if not base:
            return {"items": [], "total": 0}
        scores: dict[int, tuple[float, dict]] = {}
        for base_row in base:
            base_vector = unpack_vector(base_row["vector"], int(base_row["dim"] or 0))
            if not base_vector:
                continue
            rows = conn.execute(
                """
                SELECT e.media_id, e.dim, e.vector, m.*, GROUP_CONCAT(t.tag, ',') AS tags
                FROM media_embeddings e
                JOIN media_items m ON m.id=e.media_id
                LEFT JOIN media_tags t ON t.media_id=m.id AND t.state != 'rejected'
                WHERE e.kind=? AND e.model=? AND e.media_id != ? AND m.risk_state='normal'
                GROUP BY e.media_id, e.kind, e.model
                """,
                (base_row["kind"], base_row["model"], media_id),
            ).fetchall()
            weight = 1.0 if base_row["kind"] == "image" else 0.75
            for row in rows:
                data = dict(row)
                vector = unpack_vector(data.pop("vector", None), int(data.get("dim") or 0))
                score = cosine_similarity(base_vector, vector) * weight
                candidate_id = int(data["media_id"])
                if score > scores.get(candidate_id, (0.0, {}))[0]:
                    scores[candidate_id] = (score, data)
        items = []
        for score, data in sorted(scores.values(), key=lambda item: item[0], reverse=True)[:limit]:
            data["semantic_score"] = round(score, 6)
            items.append(data)
    return {"items": items, "total": len(items)}


def risk_queue(limit: int = 100) -> dict:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT m.*, GROUP_CONCAT(t.tag, ',') AS tags
            FROM media_items m
            LEFT JOIN media_tags t ON t.media_id=m.id
            WHERE m.risk_state != 'normal' OR EXISTS (
                SELECT 1 FROM media_tags rt WHERE rt.media_id=m.id AND rt.category='risk'
            )
            GROUP BY m.id
            ORDER BY m.mtime DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return {"items": [dict(row) for row in rows], "total": len(rows)}


def media_detail(media_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM media_items WHERE id=?", (media_id,)).fetchone()
        if row is None:
            return None
        tags = conn.execute("SELECT tag, category, confidence, source, state FROM media_tags WHERE media_id=? ORDER BY category, tag", (media_id,)).fetchall()
        timeline = conn.execute(
            """
            SELECT start_seconds, end_seconds, label, confidence, source, representative_frame
            FROM media_timeline_segments
            WHERE media_id=?
            ORDER BY start_seconds, id
            """,
            (media_id,),
        ).fetchall()
        ops = conn.execute("SELECT operation, detail, created_at FROM media_operations WHERE media_id=? OR media_id IS NULL ORDER BY id DESC LIMIT 30", (media_id,)).fetchall()
        transcript = conn.execute("SELECT language, text, segments_json, model, source, updated_at FROM media_transcripts WHERE media_id=?", (media_id,)).fetchone()
    data = dict(row)
    data.update(original_source_for_media(data))
    if data.get("display_original_name"):
        data["original_name"] = data["display_original_name"]
    data["tags"] = [dict(item) for item in tags]
    data["favorite"] = 1 if any(item["tag"] == "Favorite" and item["state"] != "rejected" for item in tags) else 0
    data["timeline"] = [dict(item) for item in timeline]
    data["operations"] = [dict(item) for item in ops]
    if transcript is not None:
        transcript_data = dict(transcript)
        try:
            transcript_data["segments"] = json.loads(transcript_data.pop("segments_json") or "[]")
        except Exception:
            transcript_data["segments"] = []
        data["transcript"] = transcript_data
    data["contact_sheet"] = contact_sheet_for_media(data)
    return data


def contact_sheet_for_media(data: dict) -> str:
    if data.get("media_type") != "video":
        return ""
    root = Path(data.get("root") or output_root()).resolve()
    relative_path = str(data.get("relative_path") or "")
    if not relative_path:
        return ""
    for row in read_csv(root / "_MANIFESTS" / "frame_index.csv"):
        if row.get("media_path") == relative_path:
            sheet = row.get("contact_sheet") or ""
            if not sheet:
                return ""
            candidate = (root / sheet).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                return ""
            if candidate.exists() and candidate.is_file():
                return sheet
            return ""
    return ""


def original_source_for_media(data: dict) -> dict:
    root = Path(data.get("root") or output_root())
    rel_path = data.get("relative_path", "")
    filename = data.get("filename", "")
    current_original = data.get("original_name", "")
    hash_value = data.get("sha256", "")
    hash8 = data.get("hash8", "")
    result = trace_original_source(root, rel_path, hash_value, hash8, current_original or filename)
    if not result.get("display_original_name"):
        result["display_original_name"] = current_original or filename
    return result


def media_for_author(author: str, media_type: str = "all", limit: int = 80, offset: int = 0) -> dict:
    author = author.strip()
    if not author:
        return {"total": 0, "limit": limit, "offset": offset, "items": []}
    clauses = ["m.risk_state='normal'"]
    params: list[object] = []
    if media_type in {"photo", "video"}:
        clauses.append("m.media_type=?")
        params.append(media_type)
    actor_path = f"Actors/{author}/%"
    like = f"%{author}%"
    clauses.append(
        """
        (
            m.author LIKE ?
            OR m.person LIKE ?
            OR m.relative_path LIKE ?
            OR EXISTS (
                SELECT 1 FROM media_tags t
                WHERE t.media_id=m.id
                  AND t.state != 'rejected'
                  AND (t.tag LIKE ? OR (t.category='author' AND t.tag=?))
            )
        )
        """
    )
    params.extend([like, like, actor_path, like, author])
    where = f"WHERE {' AND '.join(clauses)}"
    with connect() as conn:
        total = int(conn.execute(f"SELECT COUNT(DISTINCT m.id) AS c FROM media_items m {where}", params).fetchone()["c"])
        rows = conn.execute(
            f"""
            SELECT m.*, GROUP_CONCAT(t.tag, ',') AS tags
            FROM media_items m
            LEFT JOIN media_tags t ON t.media_id=m.id AND t.state != 'rejected'
            {where}
            GROUP BY m.id
            ORDER BY m.mtime DESC, m.id DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()
    return {"total": total, "limit": limit, "offset": offset, "items": [dict(row) for row in rows]}


def tag_graph(limit_nodes: int = 80, limit_edges: int = 180, min_edge: int = 2) -> dict:
    with connect() as conn:
        tag_rows = conn.execute(
            """
            SELECT tag, category, COUNT(DISTINCT media_id) AS media_count, AVG(confidence) AS confidence
            FROM media_tags
            WHERE state != 'rejected' AND tag != ''
            GROUP BY tag, category
            ORDER BY media_count DESC, tag
            LIMIT ?
            """,
            (limit_nodes,),
        ).fetchall()
        tags = [dict(row) for row in tag_rows]
        allowed = {row["tag"] for row in tags}
        edge_counts: defaultdict[tuple[str, str], int] = defaultdict(int)
        if allowed:
            media_tags = conn.execute(
                """
                SELECT media_id, tag
                FROM media_tags
                WHERE state != 'rejected' AND tag != ''
                ORDER BY media_id, tag
                """
            ).fetchall()
            grouped: defaultdict[int, set[str]] = defaultdict(set)
            for row in media_tags:
                tag = row["tag"]
                if tag in allowed:
                    grouped[int(row["media_id"])].add(tag)
            for values in grouped.values():
                sorted_tags = sorted(values)
                for left_index, left in enumerate(sorted_tags):
                    for right in sorted_tags[left_index + 1:]:
                        edge_counts[(left, right)] += 1
        edges = [
            {"source": left, "target": right, "weight": count}
            for (left, right), count in edge_counts.items()
            if count >= min_edge
        ]
        edges.sort(key=lambda item: (-item["weight"], item["source"], item["target"]))
    return {"nodes": tags, "edges": edges[:limit_edges]}


def media_by_relative_paths(root: Path, relative_paths: list[str], limit: int = 120) -> dict:
    clean = []
    names = []
    for item in relative_paths:
        if not item:
            continue
        normalized = Path(item).as_posix()
        clean.append(normalized)
        name = Path(item).name
        if name:
            names.append(name)
    clean = sorted(set(clean))
    names = sorted(set(names))
    if not clean:
        return {"items": [], "total": 0}
    path_placeholders = ",".join("?" for _ in clean)
    name_placeholders = ",".join("?" for _ in names) if names else "''"
    conditions = [
        f"m.relative_path IN ({path_placeholders})",
        f"m.normalized_path IN ({path_placeholders})",
    ]
    params: list[object] = [*clean, *clean]
    if names:
        conditions.extend([
            f"m.filename IN ({name_placeholders})",
            f"m.original_name IN ({name_placeholders})",
        ])
        params.extend([*names, *names])
    where = " OR ".join(conditions)
    with connect() as conn:
        total = int(conn.execute(f"SELECT COUNT(DISTINCT m.id) AS c FROM media_items m WHERE {where}", params).fetchone()["c"])
        rows = conn.execute(
            f"""
            SELECT m.*, GROUP_CONCAT(t.tag, ',') AS tags
            FROM media_items m
            LEFT JOIN media_tags t ON t.media_id=m.id AND t.state != 'rejected'
            WHERE {where}
            GROUP BY m.id
            ORDER BY m.mtime DESC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()
    return {"items": [dict(row) for row in rows], "total": total}


SENSEVOICE_TOKEN_TAGS = {
    "HAPPY": ("voice_mood", "笑声愉悦", 0.76),
    "SAD": ("voice_mood", "哭腔低落", 0.72),
    "ANGRY": ("voice_mood", "强势命令", 0.70),
    "NEUTRAL": ("voice_mood", "普通对白", 0.60),
    "BGM": ("audio_event", "背景音乐", 0.82),
    "MUSIC": ("audio_event", "背景音乐", 0.82),
    "LAUGHTER": ("audio_event", "笑声", 0.86),
    "LAUGH": ("audio_event", "笑声", 0.86),
    "CRYING": ("audio_event", "哭声", 0.80),
    "COUGH": ("audio_event", "咳嗽", 0.76),
    "APPLAUSE": ("audio_event", "掌声", 0.72),
    "SNEEZE": ("audio_event", "喷嚏", 0.72),
}

LANGUAGE_TAGS = {
    "zh": "中文",
    "yue": "粤语",
    "en": "英语",
    "ja": "日语",
    "ko": "韩语",
}

AUDIO_TEXT_RULES = [
    ("voice_mood", "撒娇", 0.72, ["哥哥", "不要嘛", "好不好嘛", "人家", "讨厌啦"]),
    ("voice_mood", "害羞", 0.68, ["害羞", "不好意思", "别看", "不要看"]),
    ("voice_mood", "挑逗", 0.72, ["想不想", "喜欢吗", "舒服吗", "乖", "听话"]),
    ("voice_mood", "低语耳语", 0.68, ["小声", "悄悄", "耳边"]),
    ("voice_style", "甜妹音", 0.62, ["哥哥", "呀", "嘛", "啦"]),
    ("voice_style", "成熟声线", 0.58, ["姐姐", "听话", "乖一点"]),
    ("voice_style", "软萌声线", 0.58, ["人家", "不要嘛", "好嘛"]),
    ("shooting_method", "自拍口播", 0.70, ["大家好", "今天", "视频", "直播"]),
    ("content_type", "剧情对白", 0.65, ["老师", "同学", "主人", "哥哥", "姐姐"]),
]


def clean_sensevoice_text(text: str) -> tuple[str, list[str]]:
    tokens = re.findall(r"<\|([^|<>]+)\|>", text)
    cleaned = re.sub(r"<\|[^|<>]+\|>", "", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned, tokens


def audio_tags_for_transcript(text: str, language: str, source: str) -> list[dict]:
    cleaned, tokens = clean_sensevoice_text(text)
    lowered = cleaned.lower()
    tags: dict[tuple[str, str], dict] = {}
    if language:
        label = LANGUAGE_TAGS.get(language.lower(), language)
        tags[("voice_language", label)] = {"tag": label, "category": "voice_language", "confidence": 0.95, "source": source, "state": "confirmed"}
    for token in tokens:
        key = token.upper()
        language_key = token.lower()
        if language_key in LANGUAGE_TAGS:
            label = LANGUAGE_TAGS[language_key]
            tags[("voice_language", label)] = {"tag": label, "category": "voice_language", "confidence": 0.95, "source": source, "state": "confirmed"}
        if key in SENSEVOICE_TOKEN_TAGS:
            category, label, confidence = SENSEVOICE_TOKEN_TAGS[key]
            tags[(category, label)] = {"tag": label, "category": category, "confidence": confidence, "source": source, "state": "confirmed" if confidence >= 0.7 else "pending"}
    for category, label, confidence, words in AUDIO_TEXT_RULES:
        if any(word.lower() in lowered for word in words):
            tags[(category, label)] = {"tag": label, "category": category, "confidence": confidence, "source": source, "state": "confirmed" if confidence >= 0.7 else "pending"}
    if cleaned:
        tags[("audio_event", "有人声")] = {"tag": "有人声", "category": "audio_event", "confidence": 0.9, "source": source, "state": "confirmed"}
    return list(tags.values())


def configured_seconds(env_name: str, default: int = 0) -> int:
    value = (os.environ.get(env_name, str(default)) or str(default)).strip()
    try:
        return max(0, int(value))
    except ValueError:
        return default


def cancel_requested() -> bool:
    cancel_file = os.environ.get("TGMM_CANCEL_FILE", "")
    return bool(cancel_file and Path(cancel_file).exists())


def run_cancelable_command(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.Popen(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    while True:
        try:
            stdout, stderr = proc.communicate(timeout=0.5)
            return proc.returncode or 0, stdout or "", stderr or ""
        except subprocess.TimeoutExpired:
            if not cancel_requested():
                continue
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except Exception:
                proc.terminate()
            try:
                stdout, stderr = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except Exception:
                    proc.kill()
                stdout, stderr = proc.communicate()
            return 130, stdout or "", (stderr or "") + "\ncancelled"


def extract_audio_wav(video: Path, wav: Path, max_seconds: int | None = None) -> tuple[bool, str]:
    cmd = ["ffmpeg", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000"]
    seconds = configured_seconds("TRANSCRIBE_MAX_SECONDS", 0) if max_seconds is None else max(0, int(max_seconds))
    if seconds > 0:
        cmd.extend(["-t", str(seconds)])
    cmd.append(str(wav))
    returncode, _stdout, stderr = run_cancelable_command(cmd)
    return returncode == 0 and wav.exists() and wav.stat().st_size > 0, stderr[-1000:]


def sensevoice_command(wav: Path) -> list[str] | None:
    model = os.environ.get("SENSEVOICE_GGUF_MODEL", "/models/sensevoice/SenseVoiceSmall.gguf")
    binary = os.environ.get("SENSEVOICE_GGUF_BIN", "llama-sensevoice")
    template = os.environ.get("SENSEVOICE_GGUF_COMMAND", "")
    if template:
        return [part.format(audio=str(wav), model=model, bin=binary) for part in shlex.split(template)]
    model_root = Path(os.environ.get("MODEL_ROOT", "/models"))
    runtime = model_root / "sensevoice" / "bin" / "llama-funasr-sensevoice"
    vad = model_root / "sensevoice" / "fsmn-vad.gguf"
    bundled_runtime = Path("/usr/local/bin/llama-funasr-sensevoice")
    if bundled_runtime.exists() and Path(model).exists() and vad.exists():
        return [str(bundled_runtime), "-m", model, "--vad", str(vad), "-a", str(wav)]
    if runtime.exists() and Path(model).exists() and vad.exists():
        return [str(runtime), "-m", model, "--vad", str(vad), "-a", str(wav)]
    found = shutil.which(binary) or shutil.which("sensevoice-cli") or shutil.which("llama-sensevoice") or shutil.which("llama-funasr-sensevoice")
    if not found or not Path(model).exists():
        return None
    if Path(found).name == "llama-funasr-sensevoice" and vad.exists():
        return [found, "-m", model, "--vad", str(vad), "-a", str(wav)]
    return [found, "-m", model, "-f", str(wav), "--language", "auto"]


def parse_sensevoice_output(stdout: str) -> tuple[str, str, list[dict]]:
    text = stdout.strip()
    language = ""
    segments: list[dict] = []
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            language = str(data.get("language") or data.get("lang") or "")
            raw_text = str(data.get("text") or data.get("result") or "")
            raw_segments = data.get("segments") or data.get("sentence_info") or []
            if isinstance(raw_segments, list):
                for item in raw_segments:
                    if not isinstance(item, dict):
                        continue
                    start = float(item.get("start", item.get("start_ms", 0)) or 0)
                    end = float(item.get("end", item.get("end_ms", 0)) or 0)
                    if start > 1000 or end > 1000:
                        start /= 1000
                        end /= 1000
                    segment_text = str(item.get("text") or "")
                    segments.append({"start": round(start, 2), "end": round(end, 2), "text": clean_sensevoice_text(segment_text)[0]})
            text = raw_text or "\n".join(item["text"] for item in segments)
        elif isinstance(data, list):
            parts = []
            for item in data:
                if isinstance(item, dict):
                    parts.append(str(item.get("text") or ""))
            text = "\n".join(parts).strip()
    except Exception:
        pass
    cleaned, tokens = clean_sensevoice_text(text)
    for token in tokens:
        if token.lower() in LANGUAGE_TAGS:
            language = token.lower()
    if not segments and cleaned:
        segments = [{"start": 0, "end": 0, "text": cleaned}]
    return cleaned, language, segments


def transcribe_with_sensevoice_gguf(wav: Path) -> dict | None:
    cmd = sensevoice_command(wav)
    if not cmd:
        return None
    returncode, stdout, stderr = run_cancelable_command(cmd)
    if returncode != 0:
        return {"ok": False, "cancelled": returncode == 130, "error": stderr[-1000:] or f"exit {returncode}", "engine": "sensevoice-gguf"}
    text, language, segments = parse_sensevoice_output(stdout)
    return {
        "ok": True,
        "text": text,
        "tag_text": stdout,
        "language": language,
        "segments": segments,
        "engine": "sensevoice-gguf",
        "raw": stdout[-2000:],
    }


def funasr_nano_command(wav: Path) -> list[str] | None:
    template = os.environ.get("FUNASR_NANO_COMMAND", "").strip()
    if template:
        return [part.format(audio=str(wav), model=os.environ.get("FUNASR_NANO_MODEL", ""), model_dir=os.environ.get("FUNASR_NANO_MODEL_DIR", "/models/funasr-nano")) for part in shlex.split(template)]
    found = shutil.which("sherpa-onnx-offline") or shutil.which("funasr-nano") or shutil.which("funasr-onnx")
    model_dir = Path(os.environ.get("FUNASR_NANO_MODEL_DIR", "/models/funasr-nano"))
    if found and model_dir.exists():
        return [found, "--model-dir", str(model_dir), "--tokens", str(model_dir / "tokens.txt"), str(wav)]
    return None


def parse_generic_asr_output(stdout: str) -> tuple[str, str, list[dict]]:
    text = stdout.strip()
    language = ""
    segments: list[dict] = []
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            language = str(data.get("language") or data.get("lang") or "")
            raw_segments = data.get("segments") or data.get("sentence_info") or data.get("timestamps") or []
            if isinstance(raw_segments, list):
                for item in raw_segments:
                    if not isinstance(item, dict):
                        continue
                    segment_text = str(item.get("text") or item.get("sentence") or "").strip()
                    if not segment_text:
                        continue
                    start = float(item.get("start", item.get("start_ms", 0)) or 0)
                    end = float(item.get("end", item.get("end_ms", 0)) or 0)
                    if start > 1000 or end > 1000:
                        start /= 1000
                        end /= 1000
                    segments.append({"start": round(start, 2), "end": round(end, 2), "text": segment_text})
            text = str(data.get("text") or data.get("result") or data.get("transcript") or "\n".join(item["text"] for item in segments)).strip()
        elif isinstance(data, list):
            parts = []
            for item in data:
                if isinstance(item, dict):
                    parts.append(str(item.get("text") or item.get("sentence") or ""))
            text = "\n".join(part for part in parts if part).strip()
    except Exception:
        pass
    text = re.sub(r"\s+", " ", text).strip()
    if not segments and text:
        segments = [{"start": 0, "end": 0, "text": text}]
    return text, language, segments


def transcribe_with_funasr_nano_onnx(wav: Path) -> dict | None:
    cmd = funasr_nano_command(wav)
    if not cmd:
        return None
    returncode, stdout, stderr = run_cancelable_command(cmd)
    if returncode != 0:
        return {"ok": False, "cancelled": returncode == 130, "error": stderr[-1000:] or f"exit {returncode}", "engine": "funasr-nano-onnx"}
    text, language, segments = parse_generic_asr_output(stdout)
    return {
        "ok": True,
        "text": text,
        "tag_text": text,
        "language": language,
        "segments": segments,
        "engine": "funasr-nano-onnx",
        "model": os.environ.get("FUNASR_NANO_MODEL_DIR", "/models/funasr-nano"),
        "raw": stdout[-2000:],
    }


def transcribe_with_faster_whisper(wav: Path, model, model_name: str) -> dict:
    segments_iter, info = model.transcribe(str(wav), vad_filter=True)
    segments = [
        {"start": round(float(seg.start), 2), "end": round(float(seg.end), 2), "text": seg.text.strip()}
        for seg in segments_iter
        if seg.text.strip()
    ]
    text = "\n".join(item["text"] for item in segments)
    return {
        "ok": True,
        "text": text,
        "tag_text": text,
        "language": getattr(info, "language", "") or "",
        "segments": segments,
        "engine": "faster-whisper",
        "model": model_name,
    }


def subtitle_dir(root: Path | None = None) -> Path:
    base = root or output_root()
    return base / "_MANIFESTS" / "subtitles"


def vtt_timestamp(value: object) -> str:
    total_ms = max(0, int(round(float(value or 0) * 1000)))
    hours, rem = divmod(total_ms, 3600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def vtt_escape(text: object) -> str:
    return str(text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").strip()


def transcript_to_vtt(segments: list[dict], text: str = "", mode: str = "original") -> str:
    rows = ["WEBVTT", ""]
    clean_segments = [item for item in segments if isinstance(item, dict) and str(item.get("text") or "").strip()]
    if not clean_segments and text.strip():
        clean_segments = [{"start": 0, "end": 5, "text": text.strip()}]
    for index, item in enumerate(clean_segments, start=1):
        start = float(item.get("start", item.get("start_seconds", 0)) or 0)
        end = float(item.get("end", item.get("end_seconds", 0)) or 0)
        if end <= start:
            end = start + 4
        original = vtt_escape(item.get("text", ""))
        translated = vtt_escape(item.get("translation_zh") or item.get("zh") or item.get("translated_text") or "")
        cue_text = original
        if mode == "bilingual" and translated and translated != original:
            cue_text = f"{original}\n{translated}"
        rows.extend([str(index), f"{vtt_timestamp(start)} --> {vtt_timestamp(end)}", cue_text, ""])
    return "\n".join(rows)


def timed_transcript_segments(segments: list[dict]) -> list[dict]:
    out: list[dict] = []
    for item in segments:
        if not isinstance(item, dict) or not str(item.get("text") or "").strip():
            continue
        try:
            start = float(item.get("start", item.get("start_seconds", 0)) or 0)
            end = float(item.get("end", item.get("end_seconds", 0)) or 0)
        except (TypeError, ValueError):
            continue
        if end <= start or (start == 0 and end <= 4 and len(str(item.get("text") or "")) > 240):
            continue
        out.append(item)
    return out


def write_subtitle_files(conn, media_id: int, segments: list[dict], text: str) -> bool:
    timed = timed_transcript_segments(segments)
    if not timed:
        return False
    row = conn.execute("SELECT root FROM media_items WHERE id=?", (media_id,)).fetchone()
    root = Path(row["root"]) if row and row["root"] else output_root()
    out_dir = subtitle_dir(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{media_id}.vtt").write_text(transcript_to_vtt(timed, text, "original"), encoding="utf-8")
    (out_dir / f"{media_id}.bilingual.vtt").write_text(transcript_to_vtt(timed, text, "bilingual"), encoding="utf-8")
    return True


def remove_subtitle_files(conn, media_id: int) -> None:
    row = conn.execute("SELECT root FROM media_items WHERE id=?", (media_id,)).fetchone()
    root = Path(row["root"]) if row and row["root"] else output_root()
    for suffix in (".vtt", ".bilingual.vtt"):
        (subtitle_dir(root) / f"{media_id}{suffix}").unlink(missing_ok=True)


def subtitle_for_media(media_id: int, mode: str = "original") -> tuple[str, Path | None]:
    suffix = ".bilingual.vtt" if mode == "bilingual" else ".vtt"
    with connect() as conn:
        media = conn.execute("SELECT root FROM media_items WHERE id=?", (media_id,)).fetchone()
        transcript = conn.execute("SELECT text, segments_json FROM media_transcripts WHERE media_id=?", (media_id,)).fetchone()
    if media is None:
        raise KeyError("Media not found")
    root = Path(media["root"]) if media["root"] else output_root()
    if transcript is None:
        return "", None
    try:
        segments = json.loads(transcript["segments_json"] or "[]")
    except Exception:
        segments = []
    timed = timed_transcript_segments(segments)
    if not timed:
        return "", None
    path = subtitle_dir(root) / f"{media_id}{suffix}"
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace"), path
    return transcript_to_vtt(timed, str(transcript["text"] or ""), mode), None


def save_audio_tags(conn, media_id: int, tag_text: str, language: str, source: str, replace: bool = True) -> int:
    if replace:
        conn.execute("DELETE FROM media_tags WHERE media_id=? AND source=?", (media_id, source))
    inserted = 0
    for tag in audio_tags_for_transcript(tag_text, language, source):
        conn.execute(
            """
            INSERT OR REPLACE INTO media_tags (media_id, tag, category, confidence, source, state)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (media_id, tag["tag"], tag["category"], tag["confidence"], tag["source"], tag["state"]),
        )
        inserted += 1
    return inserted


def save_transcript(conn, media_id: int, result: dict, model_name: str, include_text_tags: bool = True) -> None:
    text = str(result.get("text") or "")
    language = str(result.get("language") or "")
    segments = result.get("segments") or []
    engine = str(result.get("engine") or "unknown")
    conn.execute(
        """
        INSERT INTO media_transcripts (media_id, language, text, segments_json, model, source, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(media_id) DO UPDATE SET
            language=excluded.language,
            text=excluded.text,
            segments_json=excluded.segments_json,
            model=excluded.model,
            source=excluded.source,
            updated_at=CURRENT_TIMESTAMP
        """,
        (media_id, language, text, json.dumps(segments, ensure_ascii=False), model_name, engine),
    )
    conn.execute("DELETE FROM media_tags WHERE media_id=? AND source IN ('audio', 'sensevoice-gguf', 'faster-whisper', 'transcript', 'sensevoice-audio', 'funasr-nano-onnx')", (media_id,))
    if include_text_tags:
        tag_text = str(result.get("tag_text") or text)
        tag_source = "sensevoice-audio" if engine == "sensevoice-gguf" else "transcript"
        save_audio_tags(conn, media_id, tag_text, language, tag_source, replace=False)
    conn.execute(
        "INSERT INTO media_operations (media_id, operation, detail) VALUES (?, 'transcribe', ?)",
        (media_id, f"segments={len(segments)} model={model_name} engine={engine}"),
    )
    try:
        if not write_subtitle_files(conn, media_id, segments, text):
            remove_subtitle_files(conn, media_id)
    except OSError:
        pass


def transcript_needs_timed_rerun(segments_json: str | None, text: str | None = "", source: str | None = "") -> bool:
    try:
        segments = json.loads(segments_json or "[]")
    except (TypeError, json.JSONDecodeError):
        return True
    if not str(text or "").strip() and str(source or "").lower() == "faster-whisper":
        return False
    return not bool(timed_transcript_segments(segments if isinstance(segments, list) else []))


def transcription_candidates(root: Path, limit: int | None = None) -> list:
    query = """
        SELECT m.id, m.path, m.filename, tr.text AS transcript_text, tr.segments_json, tr.source AS transcript_source
        FROM media_items m
        LEFT JOIN media_transcripts tr ON tr.media_id=m.id
        WHERE m.media_type='video' AND m.root=?
        ORDER BY m.mtime DESC
    """
    with connect() as conn:
        candidates = conn.execute(query, (str(root),)).fetchall()
    rows = [
        row
        for row in candidates
        if row["segments_json"] is None
        or transcript_needs_timed_rerun(row["segments_json"], row["transcript_text"], row["transcript_source"])
    ]
    if limit is not None:
        rows = rows[:max(0, int(limit))]
    return rows


def transcribe_videos(root: Path, limit: int | None = 12, model_size: str = "base") -> dict:
    rows = transcription_candidates(root, limit)
    if not rows:
        return {"ok": True, "processed": 0, "segments": 0, "timed_subtitles": 0, "failed": 0, "errors": []}
    total = len(rows)
    print("TGMM_PROGRESS " + json.dumps({"stage": "transcribe", "processed": 0, "total": total, "progress": 0, "message": "loading model"}, ensure_ascii=False), flush=True)
    legacy_engine = os.environ.get("ASR_ENGINE", "auto").strip().lower()
    transcript_engine = os.environ.get("TRANSCRIPT_ENGINE", legacy_engine).strip().lower()
    audio_tag_mode = os.environ.get("AUDIO_TAG_MODE", "sensevoice-sample").strip().lower()
    audio_tag_sample_seconds = configured_seconds("AUDIO_TAG_SAMPLE_SECONDS", 30)
    generate_timed_subtitles = os.environ.get("GENERATE_TIMED_SUBTITLES", "true").strip().lower() in {"1", "true", "yes", "on"}
    if transcript_engine == "whisper":
        transcript_engine = "faster-whisper"
    if transcript_engine == "sensevoice":
        transcript_engine = "sensevoice-gguf"
    sensevoice_available = sensevoice_command(Path("__probe__.wav")) is not None
    funasr_available = funasr_nano_command(Path("__probe__.wav")) is not None
    model = None
    model_name = os.environ.get("WHISPER_MODEL", model_size)
    should_load_whisper = transcript_engine in {"faster-whisper", "whisper"} or (transcript_engine == "auto" and not funasr_available and not sensevoice_available)
    if should_load_whisper:
        try:
            from faster_whisper import WhisperModel  # type: ignore
            device = os.environ.get("WHISPER_DEVICE", "cpu")
            compute_type = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")
            model = WhisperModel(model_name, device=device, compute_type=compute_type, download_root=os.environ.get("MODEL_ROOT", "/models"))
        except Exception as exc:
            if transcript_engine != "auto":
                return {
                    "ok": False,
                    "error": "faster-whisper is not installed in this image. Install the transcribe extra or build a transcribe-enabled image.",
                    "detail": repr(exc),
                }
    processed = 0
    segment_count = 0
    errors = []
    warnings = []
    timed_count = 0
    with TemporaryDirectory(prefix="tgmm_audio_") as tmpdir:
        tmp_root = Path(tmpdir)
        with connect() as conn:
            for index, row in enumerate(rows, start=1):
                cancel_file = os.environ.get("TGMM_CANCEL_FILE", "")
                if cancel_file and Path(cancel_file).exists():
                    return {"ok": False, "processed": processed, "segments": segment_count, "cancelled": True, "errors": errors[:20]}
                path = Path(row["path"])
                if not path.exists():
                    errors.append({"id": row["id"], "error": "media file missing"})
                    continue
                wav = tmp_root / f"{row['id']}.wav"
                ok, audio_error = extract_audio_wav(path, wav)
                if not ok:
                    errors.append({"id": row["id"], "error": audio_error})
                    continue
                try:
                    result = None
                    if transcript_engine in {"auto", "funasr-nano-onnx", "funasr-nano"} and funasr_available:
                        result = transcribe_with_funasr_nano_onnx(wav)
                        if result and not result.get("ok"):
                            if transcript_engine != "auto":
                                errors.append({"id": row["id"], "error": result.get("error", "funasr-nano failed")})
                                continue
                            warnings.append({"id": row["id"], "warning": "funasr-nano fallback", "detail": result.get("error", "funasr-nano failed")})
                            result = None
                    if result is None and transcript_engine in {"auto", "sensevoice", "sensevoice-gguf"} and sensevoice_available:
                        result = transcribe_with_sensevoice_gguf(wav)
                        if result and not result.get("ok"):
                            if transcript_engine != "auto":
                                errors.append({"id": row["id"], "error": result.get("error", "sensevoice failed")})
                                continue
                            warnings.append({"id": row["id"], "warning": "sensevoice fallback", "detail": result.get("error", "sensevoice failed")})
                            result = None
                    if result is None:
                        if transcript_engine == "auto" and model is None:
                            try:
                                from faster_whisper import WhisperModel  # type: ignore
                                device = os.environ.get("WHISPER_DEVICE", "cpu")
                                compute_type = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")
                                model = WhisperModel(model_name, device=device, compute_type=compute_type, download_root=os.environ.get("MODEL_ROOT", "/models"))
                            except Exception as exc:
                                errors.append({"id": row["id"], "error": f"fallback faster-whisper unavailable: {exc!r}"})
                        if model is None:
                            errors.append({"id": row["id"], "error": "no ASR engine available"})
                            continue
                        result = transcribe_with_faster_whisper(wav, model, model_name)
                    if result and not timed_transcript_segments(result.get("segments") or []) and generate_timed_subtitles:
                        if model is None:
                            try:
                                from faster_whisper import WhisperModel  # type: ignore
                                device = os.environ.get("WHISPER_DEVICE", "cpu")
                                compute_type = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")
                                model = WhisperModel(model_name, device=device, compute_type=compute_type, download_root=os.environ.get("MODEL_ROOT", "/models"))
                            except Exception as exc:
                                warnings.append({"id": row["id"], "warning": "timed subtitle fallback unavailable", "detail": repr(exc)})
                        if model is not None:
                            timed_result = transcribe_with_faster_whisper(wav, model, model_name)
                            if timed_transcript_segments(timed_result.get("segments") or []):
                                result = timed_result
                            else:
                                warnings.append({"id": row["id"], "warning": "ASR returned transcript without usable timestamps"})
                    save_transcript(conn, int(row["id"]), result, result.get("model") or os.environ.get("SENSEVOICE_GGUF_MODEL", "SenseVoiceSmall.gguf"), include_text_tags=audio_tag_mode != "off")
                    if result.get("engine") != "sensevoice-gguf" and audio_tag_mode in {"sensevoice-sample", "sensevoice-full"} and sensevoice_available:
                        tag_wav = wav
                        if audio_tag_mode == "sensevoice-sample" and audio_tag_sample_seconds > 0:
                            tag_wav = tmp_root / f"{row['id']}.tags.wav"
                            tag_ok, tag_audio_error = extract_audio_wav(path, tag_wav, audio_tag_sample_seconds)
                            if not tag_ok:
                                warnings.append({"id": row["id"], "warning": "audio tag sample failed", "detail": tag_audio_error})
                                tag_wav = None
                        if tag_wav is not None:
                            tag_result = transcribe_with_sensevoice_gguf(tag_wav)
                            if tag_result and tag_result.get("ok"):
                                tags_inserted = save_audio_tags(conn, int(row["id"]), str(tag_result.get("tag_text") or tag_result.get("text") or ""), str(tag_result.get("language") or result.get("language") or ""), "sensevoice-audio", replace=True)
                                conn.execute(
                                    "INSERT INTO media_operations (media_id, operation, detail) VALUES (?, 'audio_tag', ?)",
                                    (int(row["id"]), f"engine=sensevoice-gguf mode={audio_tag_mode} tags={tags_inserted}"),
                                )
                            elif tag_result:
                                warnings.append({"id": row["id"], "warning": "sensevoice audio tag failed", "detail": tag_result.get("error", "")})
                    conn.commit()
                    processed += 1
                    segment_count += len(result.get("segments") or [])
                    if timed_transcript_segments(result.get("segments") or []):
                        timed_count += 1
                except Exception as exc:
                    errors.append({"id": row["id"], "error": repr(exc)})
                print(
                    "TGMM_PROGRESS "
                    + json.dumps(
                        {
                            "stage": "transcribe",
                            "processed": index,
                            "total": total,
                            "progress": int(index / total * 100) if total else 0,
                            "failed": len(errors),
                            "current": str(path),
                            "message": f"transcribed {processed}/{total}",
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
    response = {
        "ok": len(errors) == 0,
        "partial": bool(processed and errors),
        "processed": processed,
        "segments": segment_count,
        "timed_subtitles": timed_count,
        "failed": len(errors),
        "errors": errors[:20],
    }
    if warnings:
        response["warnings"] = warnings[:20]
    return response


def mime_for(path: Path, media_type: str) -> str:
    guessed = mimetypes.guess_type(path.name)[0]
    if guessed:
        return guessed
    return "video/mp4" if media_type == "video" else "image/jpeg"


def dhash(path: Path) -> str:
    if Image is None or not path.exists():
        return ""
    try:
        with Image.open(path) as img:
            gray = img.convert("L").resize((9, 8))
            pixels = list(gray.getdata())
        bits = []
        for row in range(8):
            offset = row * 9
            for col in range(8):
                bits.append(1 if pixels[offset + col] > pixels[offset + col + 1] else 0)
        value = 0
        for bit in bits:
            value = (value << 1) | bit
        return f"{value:016x}"
    except Exception:
        return ""


def quick_file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            digest.update(handle.read(1024 * 1024))
        digest.update(str(path.stat().st_size).encode())
        return digest.hexdigest()
    except Exception:
        return ""


def upsert_similarity_group(conn, kind: str, signature: str, members: list[tuple[int, str, float, str]]) -> int:
    conn.execute(
        "INSERT INTO similarity_groups (kind, signature, score) VALUES (?, ?, ?) ON CONFLICT(kind, signature) DO UPDATE SET score=excluded.score",
        (kind, signature, max((score for _media_id, _role, score, _detail in members), default=1.0)),
    )
    group_id = int(conn.execute("SELECT id FROM similarity_groups WHERE kind=? AND signature=?", (kind, signature)).fetchone()["id"])
    conn.execute("DELETE FROM similarity_members WHERE group_id=?", (group_id,))
    for media_id, role, score, detail in members:
        conn.execute(
            "INSERT OR REPLACE INTO similarity_members (group_id, media_id, role, score, detail) VALUES (?, ?, ?, ?, ?)",
            (group_id, media_id, role, score, detail),
        )
    return group_id


def rebuild_similarity_index(root: Path | None = None) -> dict:
    init_db()
    root = root or output_root()
    enable_perceptual = os.environ.get("ENABLE_PERCEPTUAL_HASH", "false").lower() in {"1", "true", "yes", "on"}
    enable_quick_hash = os.environ.get("ENABLE_QUICK_HASH", "false").lower() in {"1", "true", "yes", "on"}
    exact: defaultdict[str, list[dict]] = defaultdict(list)
    perceptual: defaultdict[str, list[dict]] = defaultdict(list)
    video_fingerprints: defaultdict[str, list[dict]] = defaultdict(list)
    with connect() as conn:
        rows = [dict(row) for row in conn.execute("SELECT id, path, relative_path, media_type, size_bytes, sha256, hash8 FROM media_items").fetchall()]
        conn.execute("DELETE FROM similarity_members")
        conn.execute("DELETE FROM similarity_groups")
        for row in rows:
            path = Path(row["path"])
            if not path.exists():
                continue
            exact_sig = row.get("sha256") or (quick_file_hash(path) if enable_quick_hash else "")
            if exact_sig:
                exact[f"{row['size_bytes']}:{exact_sig}"].append(row)
            if enable_perceptual and row["media_type"] == "photo":
                sig = dhash(path)
                if sig:
                    perceptual[sig].append(row)
            elif enable_perceptual and row["media_type"] == "video":
                frames = conn.execute(
                    "SELECT representative_frame FROM media_timeline_segments WHERE media_id=? AND representative_frame != '' ORDER BY start_seconds LIMIT 3",
                    (row["id"],),
                ).fetchall()
                frame_hashes = []
                for frame in frames:
                    sig = dhash(root / frame["representative_frame"])
                    if sig:
                        frame_hashes.append(sig)
                if frame_hashes:
                    video_fingerprints["|".join(frame_hashes)].append(row)
        groups = 0
        members = 0
        for kind, bucket in [("exact", exact), ("image_phash", perceptual), ("video_fingerprint", video_fingerprints)]:
            for signature, items in bucket.items():
                if len(items) < 2:
                    continue
                ranked = sorted(items, key=lambda item: (-int(item.get("size_bytes") or 0), item["relative_path"]))
                payload = []
                for index, item in enumerate(ranked):
                    payload.append((int(item["id"]), "keep" if index == 0 else "candidate", 1.0, item["relative_path"]))
                upsert_similarity_group(conn, kind, signature, payload)
                groups += 1
                members += len(payload)
        conn.execute("INSERT INTO media_operations (operation, detail) VALUES (?, ?)", ("rebuild_similarity_index", f"groups={groups} members={members} perceptual={enable_perceptual} quick_hash={enable_quick_hash} root={root}"))
    return {"groups": groups, "members": members, "perceptual": enable_perceptual, "quick_hash": enable_quick_hash, "root": str(root)}


def similarity_groups(limit: int = 100) -> dict:
    with connect() as conn:
        groups = conn.execute(
            """
            SELECT g.id, g.kind, g.signature, g.score, COUNT(m.media_id) AS members
            FROM similarity_groups g
            JOIN similarity_members m ON m.group_id=g.id
            GROUP BY g.id
            ORDER BY members DESC, g.kind, g.id
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        out = []
        for group in groups:
            items = conn.execute(
                """
                SELECT m.role, m.score, m.detail, i.id, i.filename, i.relative_path, i.media_type, i.author, i.quality
                FROM similarity_members m
                JOIN media_items i ON i.id=m.media_id
                WHERE m.group_id=?
                ORDER BY CASE m.role WHEN 'keep' THEN 0 ELSE 1 END, i.size_bytes DESC
                """,
                (group["id"],),
            ).fetchall()
            data = dict(group)
            data["items"] = [dict(item) for item in items]
            out.append(data)
    return {"groups": out}

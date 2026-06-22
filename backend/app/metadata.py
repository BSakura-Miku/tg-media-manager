from __future__ import annotations

import csv
import mimetypes
import os
import re
import time
from io import StringIO
from pathlib import Path

from .db import connect, get_settings, init_db


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


def manifest_maps(root: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    manifests = root / "_MANIFESTS"
    manifest = {}
    for row in read_csv(manifests / "manifest_all.csv"):
        original = row.get("original_path", "")
        if original:
            manifest[original] = row
    applied = {}
    for row in read_csv(manifests / "applied_moves.csv"):
        new_path = row.get("new_path", "")
        if new_path:
            applied[new_path] = row
    return manifest, applied


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


def upsert_media(conn, root: Path, path: Path, media_type: str, manifest: dict, applied: dict) -> int:
    stat = path.stat()
    rel_path = safe_relative(root, path)
    parsed = parse_filename(path.name, path)
    original_name = manifest.get("original_name") or Path(applied.get("original_path", "")).name or path.name
    width = int(float(manifest["width"])) if manifest.get("width") else None
    height = int(float(manifest["height"])) if manifest.get("height") else None
    duration = float(manifest["duration"]) if manifest.get("duration") else None
    resolution = parsed.get("resolution") or (f"{width}x{height}" if width and height else "")
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
        "sha256": manifest.get("hash", ""),
        "hash8": manifest.get("hash8", ""),
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


def rebuild_metadata_index(root: Path | None = None) -> dict:
    init_db()
    root = root or output_root()
    manifest_by_original, applied_by_new = manifest_maps(root)
    indexed = 0
    started = time.time()
    with connect() as conn:
        seen_paths = set()
        for path, media_type in iter_media_files(root):
            rel_path = safe_relative(root, path)
            applied = applied_by_new.get(rel_path, {})
            manifest = manifest_by_original.get(applied.get("original_path", ""), {})
            upsert_media(conn, root, path, media_type, manifest, applied)
            seen_paths.add(str(path))
            indexed += 1
        if seen_paths:
            placeholders = ",".join("?" for _ in seen_paths)
            conn.execute(f"DELETE FROM media_items WHERE path NOT IN ({placeholders})", list(seen_paths))
        else:
            conn.execute("DELETE FROM media_items")
        conn.execute("INSERT INTO media_operations (operation, detail) VALUES (?, ?)", ("rebuild_metadata_index", f"indexed={indexed} root={root}"))
    return {"indexed": indexed, "root": str(root), "elapsed_seconds": round(time.time() - started, 3)}


def media_query(q: str = "", media_type: str = "all", tag: str = "", author: str = "", limit: int = 100, offset: int = 0) -> dict:
    clauses = []
    params: list[object] = []
    if media_type in {"photo", "video"}:
        clauses.append("m.media_type=?")
        params.append(media_type)
    if author:
        clauses.append("m.author LIKE ?")
        params.append(f"%{author}%")
    if tag:
        clauses.append("EXISTS (SELECT 1 FROM media_tags t WHERE t.media_id=m.id AND t.tag LIKE ?)")
        params.append(f"%{tag}%")
    if q:
        clauses.append("(m.filename LIKE ? OR m.original_name LIKE ? OR m.author LIKE ? OR m.person LIKE ? OR m.scene LIKE ? OR m.platform LIKE ? OR m.quality LIKE ? OR EXISTS (SELECT 1 FROM media_tags t WHERE t.media_id=m.id AND t.tag LIKE ?))")
        like = f"%{q}%"
        params.extend([like, like, like, like, like, like, like, like])
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with connect() as conn:
        total = int(conn.execute(f"SELECT COUNT(*) AS c FROM media_items m {where}", params).fetchone()["c"])
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


def media_detail(media_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM media_items WHERE id=?", (media_id,)).fetchone()
        if row is None:
            return None
        tags = conn.execute("SELECT tag, category, confidence, source, state FROM media_tags WHERE media_id=? ORDER BY category, tag", (media_id,)).fetchall()
        ops = conn.execute("SELECT operation, detail, created_at FROM media_operations WHERE media_id=? OR media_id IS NULL ORDER BY id DESC LIMIT 30", (media_id,)).fetchall()
    data = dict(row)
    data["tags"] = [dict(item) for item in tags]
    data["operations"] = [dict(item) for item in ops]
    return data


def mime_for(path: Path, media_type: str) -> str:
    guessed = mimetypes.guess_type(path.name)[0]
    if guessed:
        return guessed
    return "video/mp4" if media_type == "video" else "image/jpeg"

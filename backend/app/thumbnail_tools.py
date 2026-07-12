from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Callable

from .db import connect, init_db
from .metadata import output_root, safe_relative

try:
    from PIL import Image, ImageOps
except Exception:  # pragma: no cover - optional runtime dependency
    Image = None
    ImageOps = None


MEDIA_THUMB_CACHE = "media_thumbs_v8"
THUMB_SIZE = (900, 900)

ProgressCallback = Callable[[str, int, int, str], None]
CancelCheck = Callable[[], bool]


def thumbnail_is_healthy(src: Path) -> bool:
    if Image is None or ImageOps is None or not src.exists():
        return False
    try:
        if src.stat().st_size < 900:
            return False
        with Image.open(src) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
            width, height = image.size
            if width < 40 or height < 40:
                return False
            sample = image.resize((min(width, 96), min(height, 96)))
            pixels = list(sample.getdata())
            total = max(1, len(pixels))
            green = sum(1 for r, g, b in pixels if g > 145 and g > r * 1.45 and g > b * 1.45) / total
            magenta = sum(1 for r, g, b in pixels if r > 145 and b > 145 and g < min(r, b) * 0.65) / total
            if green > 0.54 or magenta > 0.42:
                return False
            gray = ImageOps.grayscale(sample)
            low, high = gray.getextrema()
            if high - low < 8:
                return False
            pix = gray.load()
            rows = []
            sw, sh = gray.size
            for y in range(sh):
                rows.append(sum(pix[x, y] for x in range(sw)) / max(1, sw))
            if len(rows) > 8:
                jumps = sum(1 for a, b in zip(rows, rows[1:]) if abs(a - b) > 48)
                if jumps / max(1, len(rows) - 1) > 0.28:
                    return False
            return True
    except Exception:
        return False


def write_photo_thumbnail(src: Path, dest: Path) -> bool:
    if Image is None or ImageOps is None:
        return False
    tmp = dest.with_name(f".{dest.stem}.tmp{dest.suffix}")
    try:
        with Image.open(src) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
            resampling = getattr(Image, "Resampling", Image).LANCZOS
            image.thumbnail(THUMB_SIZE, resampling)
            dest.parent.mkdir(parents=True, exist_ok=True)
            image.save(tmp, "JPEG", quality=86, optimize=True)
        if thumbnail_is_healthy(tmp):
            tmp.replace(dest)
            return True
    except Exception:
        pass
    try:
        tmp.unlink()
    except OSError:
        pass
    return False


def write_video_thumbnail(src: Path, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f".{dest.stem}.tmp{dest.suffix}")
    try:
        tmp.unlink()
    except OSError:
        pass
    # Intentionally software decode here. This repair path is used when VAAPI/QSV
    # produced tinted or banded previews.
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        "3",
        "-i",
        str(src),
        "-frames:v",
        "1",
        "-vf",
        "thumbnail,scale='min(900,iw)':-2",
        "-q:v",
        "4",
        str(tmp),
    ]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=45)
        if proc.returncode == 0 and thumbnail_is_healthy(tmp):
            tmp.replace(dest)
            return True
    except (subprocess.SubprocessError, OSError):
        pass
    try:
        tmp.unlink()
    except OSError:
        pass
    return False


def thumbnail_path(root: Path, media_id: int) -> Path:
    return root / "_MANIFESTS" / MEDIA_THUMB_CACHE / f"{media_id}.jpg"


def thumbnail_health_summary(root: Path | None = None, sample_limit: int = 300) -> dict:
    root = root or output_root()
    init_db()
    with connect() as conn:
        total = int(conn.execute("SELECT COUNT(*) FROM media_items WHERE root=?", (str(root),)).fetchone()[0] or 0)
        rows = conn.execute(
            "SELECT id FROM media_items WHERE root=? ORDER BY id DESC LIMIT ?",
            (str(root), int(max(1, sample_limit))),
        ).fetchall()
    cache_dir = root / "_MANIFESTS" / MEDIA_THUMB_CACHE
    cached = sum(1 for _ in cache_dir.rglob("*.jpg")) if cache_dir.exists() else 0
    checked = healthy = unhealthy = missing = 0
    for row in rows:
        checked += 1
        thumb = thumbnail_path(root, int(row["id"]))
        if not thumb.exists():
            missing += 1
        elif thumbnail_is_healthy(thumb):
            healthy += 1
        else:
            unhealthy += 1
    return {
        "cache": MEDIA_THUMB_CACHE,
        "total_media": total,
        "cached_files": cached,
        "sample_checked": checked,
        "sample_healthy": healthy,
        "sample_unhealthy": unhealthy,
        "sample_missing": missing,
    }


def repair_thumbnail_cache(
    root: Path | None = None,
    limit: int | None = None,
    progress: ProgressCallback | None = None,
    cancel_check: CancelCheck | None = None,
) -> dict:
    root = root or output_root()
    init_db()
    sql = """
        SELECT id, path, relative_path, media_type
        FROM media_items
        WHERE root=?
        ORDER BY id
    """
    params: list[object] = [str(root)]
    if limit:
        sql += " LIMIT ?"
        params.append(int(limit))
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    total = len(rows)
    processed = repaired = healthy = failed = missing = skipped = 0
    started = time.time()
    if progress:
        progress("thumbnail-repair", 0, total, "")
    for row in rows:
        if cancel_check and cancel_check():
            return {
                "ok": False,
                "cancelled": True,
                "processed": processed,
                "total": total,
                "repaired": repaired,
                "healthy": healthy,
                "failed": failed,
                "missing": missing,
                "skipped": skipped,
                "elapsed_seconds": round(time.time() - started, 3),
            }
        processed += 1
        media_id = int(row["id"])
        src = Path(row["path"])
        thumb = thumbnail_path(root, media_id)
        try:
            source_is_newer = src.exists() and thumb.exists() and src.stat().st_mtime_ns > thumb.stat().st_mtime_ns
        except OSError:
            source_is_newer = False
        if thumb.exists() and not source_is_newer and thumbnail_is_healthy(thumb):
            healthy += 1
        elif not src.exists():
            missing += 1
        else:
            try:
                thumb.unlink()
            except OSError:
                pass
            ok = write_photo_thumbnail(src, thumb) if row["media_type"] == "photo" else write_video_thumbnail(src, thumb) if row["media_type"] == "video" else False
            if ok:
                repaired += 1
            else:
                failed += 1
        if progress and (processed == total or processed % 25 == 0):
            progress("thumbnail-repair", processed, total, safe_relative(root, src))
    with connect() as conn:
        conn.execute(
            "INSERT INTO media_operations (operation, detail) VALUES (?, ?)",
            (
                "repair_thumbnail_cache",
                f"processed={processed} repaired={repaired} healthy={healthy} failed={failed} missing={missing} root={root}",
            ),
        )
    if progress:
        progress("thumbnail-repair", total, total, "")
    return {
        "ok": True,
        "processed": processed,
        "total": total,
        "repaired": repaired,
        "healthy": healthy,
        "failed": failed,
        "missing": missing,
        "skipped": skipped,
        "elapsed_seconds": round(time.time() - started, 3),
    }

from __future__ import annotations

import os
import hashlib
import hmac
import subprocess
import threading
import time
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .db import connect, get_settings, init_db, rows_to_dicts, save_settings
from .jobs import ALLOWED_COMMANDS, create_job
from .media_stats import summary
from .metadata import media_detail, media_query, mime_for, rebuild_metadata_index, rebuild_similarity_index, risk_queue, similarity_groups

try:
    from PIL import Image, ImageChops, ImageOps
except Exception:
    Image = None
    ImageChops = None
    ImageOps = None


app = FastAPI(title="TG Media Manager")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class JobRequest(BaseModel):
    command: str


class FaceNameRequest(BaseModel):
    face_group: str
    actor_name: str


class FaceMergeRequest(BaseModel):
    source_group: str
    target_group: str


class FaceMergeNamedRequest(BaseModel):
    actor_name: str = ""


class ActorRenameRequest(BaseModel):
    old_name: str
    new_name: str


class ActorExcludeRequest(BaseModel):
    actor_name: str


class SettingsRequest(BaseModel):
    media_root: str
    output_root: str = ""
    source_dirs: str = ""
    language: str = "zh-CN"
    monitor_enabled: bool = False
    monitor_dirs: str = ""
    monitor_interval_minutes: int = 10


class AuthRequest(BaseModel):
    password: str


@app.on_event("startup")
def startup() -> None:
    init_db()
    start_monitor_thread()


def auth_password() -> str:
    return os.environ.get("APP_PASSWORD", "")


def auth_token() -> str:
    password = auth_password()
    if not password:
        return ""
    secret = os.environ.get("APP_SECRET", "tg-media-manager-local")
    return hashlib.sha256(f"{secret}:{password}".encode()).hexdigest()


@app.middleware("http")
async def optional_password_gate(request: Request, call_next):
    password = auth_password()
    if not password:
        return await call_next(request)
    path = request.url.path
    if path.startswith("/api/auth") or path.startswith("/assets") or path == "/api/health":
        return await call_next(request)
    cookie = request.cookies.get("tgmm_auth", "")
    if hmac.compare_digest(cookie, auth_token()):
        return await call_next(request)
    if path.startswith("/api/"):
        return JSONResponse({"detail": "Authentication required"}, status_code=401)
    return await call_next(request)


@app.get("/api/auth/status")
def api_auth_status(request: Request) -> dict:
    enabled = bool(auth_password())
    authenticated = not enabled or hmac.compare_digest(request.cookies.get("tgmm_auth", ""), auth_token())
    return {"enabled": enabled, "authenticated": authenticated, "local_only": True}


@app.post("/api/auth/login")
def api_auth_login(req: AuthRequest, response: Response) -> dict:
    if not auth_password():
        return {"ok": True, "enabled": False}
    if not hmac.compare_digest(req.password, auth_password()):
        raise HTTPException(status_code=401, detail="Invalid password")
    response.set_cookie("tgmm_auth", auth_token(), httponly=True, samesite="strict")
    return {"ok": True, "enabled": True}


@app.post("/api/auth/logout")
def api_auth_logout(response: Response) -> dict:
    response.delete_cookie("tgmm_auth")
    return {"ok": True}


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/system/hardware")
def api_system_hardware() -> dict:
    def run(args: list[str]) -> str:
        try:
            return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=8).stdout[-4000:]
        except Exception as exc:
            return repr(exc)

    return {
        "ffmpeg_hwaccel": os.environ.get("FFMPEG_HWACCEL", ""),
        "ffmpeg_hw_device": os.environ.get("FFMPEG_HW_DEVICE", ""),
        "face_providers": os.environ.get("FACE_PROVIDERS", ""),
        "openvino_device": os.environ.get("OPENVINO_DEVICE", ""),
        "dri_exists": Path("/dev/dri").exists(),
        "dri": run(["sh", "-lc", "ls -la /dev/dri 2>/dev/null || true"]),
        "ffmpeg_hwaccels": run(["ffmpeg", "-hide_banner", "-hwaccels"]),
        "vainfo": run(["sh", "-lc", "vainfo --display drm --device ${FFMPEG_HW_DEVICE:-/dev/dri/renderD128} 2>&1 | head -80 || true"]),
        "onnxruntime": run(["python", "-c", "import onnxruntime as ort; print('\\n'.join(ort.get_available_providers()))"]),
    }


@app.get("/api/summary")
def api_summary() -> dict:
    return summary()


@app.get("/api/jobs")
def api_jobs() -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT 50").fetchall()
    return rows_to_dicts(rows)


@app.get("/api/jobs/{job_id}")
def api_job(job_id: int) -> dict:
    with connect() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return dict(row)


@app.get("/api/jobs/{job_id}/log")
def api_job_log(job_id: int) -> dict:
    with connect() as conn:
        row = conn.execute("SELECT id, command, status, stdout, stderr, message FROM jobs WHERE id=?", (job_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    data = dict(row)
    return {
        "id": data["id"],
        "command": data["command"],
        "status": data["status"],
        "message": data["message"],
        "stdout": data["stdout"],
        "stderr": data["stderr"],
    }


@app.post("/api/jobs")
def api_create_job(req: JobRequest) -> dict:
    if req.command not in ALLOWED_COMMANDS:
        raise HTTPException(status_code=400, detail="Unsupported command")
    try:
        job_id = create_job(req.command)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"id": job_id}


@app.get("/api/commands")
def api_commands() -> dict:
    return {"commands": sorted(ALLOWED_COMMANDS)}


def read_csv(path: Path) -> list[dict]:
    import csv
    from io import StringIO
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8-sig", errors="replace").replace("\x00", "")
    return list(csv.DictReader(StringIO(text)))


def media_root() -> Path:
    settings = get_settings()
    return Path(settings.get("media_root") or os.environ.get("MEDIA_ROOT", "/media"))


def output_root() -> Path:
    settings = get_settings()
    return Path(settings.get("output_root") or settings.get("media_root") or os.environ.get("MEDIA_OUTPUT_ROOT") or os.environ.get("MEDIA_ROOT", "/media"))


def core_script_path() -> str:
    script = os.environ.get("CORE_SCRIPT", "/app/backend/core/tg_media_library.py")
    local_script = Path(__file__).resolve().parents[1] / "core" / "tg_media_library.py"
    if not Path(script).exists() and local_script.exists():
        script = str(local_script)
    return script


def run_core_command(command: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    settings = default_settings()
    args = ["python", core_script_path(), "--root", settings["media_root"], "--output-root", settings["output_root"], *command]
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)


def ffmpeg_hw_prefix() -> list[str]:
    mode = os.environ.get("FFMPEG_HWACCEL", "").strip().lower()
    if mode in {"", "none", "false", "0", "off"}:
        return []
    device = os.environ.get("FFMPEG_HW_DEVICE", "/dev/dri/renderD128")
    if mode in {"vaapi", "auto"} and Path(device).exists():
        return ["-hwaccel", "vaapi", "-hwaccel_device", device]
    if mode == "qsv":
        return ["-hwaccel", "qsv"]
    return []


THUMB_SIZE = (800, 520)


def trim_uniform_border(image):
    if ImageChops is None:
        return image
    try:
        bg = Image.new(image.mode, image.size, image.getpixel((0, 0)))
        diff = ImageChops.difference(image, bg)
        bbox = diff.getbbox()
    except Exception:
        return image
    if not bbox:
        return image
    left, top, right, bottom = bbox
    original_area = image.size[0] * image.size[1]
    cropped_area = max(1, right - left) * max(1, bottom - top)
    if cropped_area < original_area * 0.18:
        return image
    if (left, top, right, bottom) == (0, 0, image.size[0], image.size[1]):
        return image
    return image.crop(bbox)


def write_smart_thumbnail(src: Path, dest: Path) -> bool:
    if Image is None or ImageOps is None:
        return False
    try:
        with Image.open(src) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
            image = trim_uniform_border(image)
            resampling = getattr(Image, "Resampling", Image).LANCZOS
            image = ImageOps.fit(image, THUMB_SIZE, method=resampling, centering=(0.5, 0.35))
            dest.parent.mkdir(parents=True, exist_ok=True)
            image.save(dest, "JPEG", quality=86, optimize=True)
        return dest.exists() and dest.stat().st_size > 0
    except Exception:
        return False


def run_ffmpeg_thumbnail(src: Path, dest: Path, width: int = 800, timeout: int = 30) -> bool:
    prefixes = []
    hw = ffmpeg_hw_prefix()
    if hw:
        prefixes.append(hw)
    prefixes.append([])
    tmp = dest.with_name(f".{dest.stem}.raw.jpg")
    base_cmd = ["-ss", "00:00:02", "-i", str(src), "-frames:v", "1", "-vf", f"thumbnail,scale='min({width},iw)':-2", "-q:v", "4", str(tmp)]
    for prefix in prefixes:
        for candidate in (dest, tmp):
            if candidate.exists():
                try:
                    candidate.unlink()
                except OSError:
                    pass
        try:
            proc = subprocess.run(
                ["ffmpeg", "-y", *prefix, *base_cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout,
            )
        except (subprocess.SubprocessError, OSError):
            continue
        if proc.returncode == 0 and tmp.exists() and tmp.stat().st_size > 0 and write_smart_thumbnail(tmp, dest):
            try:
                tmp.unlink()
            except OSError:
                pass
            return True
    try:
        tmp.unlink()
    except OSError:
        pass
    return False


def default_settings() -> dict:
    settings = get_settings()
    media = settings.get("media_root") or os.environ.get("MEDIA_ROOT", "/media")
    output = settings.get("output_root") or os.environ.get("MEDIA_OUTPUT_ROOT") or media
    monitor_interval = settings.get("monitor_interval_minutes") or os.environ.get("MONITOR_INTERVAL_MINUTES", "10")
    try:
        monitor_interval_value = max(1, min(1440, int(monitor_interval)))
    except ValueError:
        monitor_interval_value = 10
    return {
        "media_root": media,
        "output_root": output,
        "source_dirs": settings.get("source_dirs") or os.environ.get("MEDIA_SOURCE_DIRS", ""),
        "language": settings.get("language") or os.environ.get("APP_LANGUAGE", "zh-CN"),
        "monitor_enabled": (settings.get("monitor_enabled") or os.environ.get("MONITOR_ENABLED", "false")).lower() in {"1", "true", "yes", "on"},
        "monitor_dirs": settings.get("monitor_dirs") or os.environ.get("MONITOR_DIRS", ""),
        "monitor_interval_minutes": monitor_interval_value,
        "monitor_last_signature": settings.get("monitor_last_signature", ""),
        "monitor_last_job_id": settings.get("monitor_last_job_id", ""),
        "monitor_last_checked_at": settings.get("monitor_last_checked_at", ""),
        "browse_roots": [item for item in os.environ.get("BROWSE_ROOTS", "/media,/library,/incoming").split(",") if item],
    }


def clean_path_value(value: str) -> str:
    value = value.strip()
    if not value.startswith("/"):
        raise HTTPException(status_code=400, detail="Path must be an absolute container path")
    return str(Path(value))


def path_in_allowed_roots(path: Path) -> bool:
    roots = [Path(item) for item in default_settings()["browse_roots"]]
    try:
        resolved = path.resolve()
    except Exception:
        resolved = path
    for root in roots:
        try:
            root_resolved = root.resolve()
        except Exception:
            root_resolved = root
        if resolved == root_resolved or root_resolved in resolved.parents:
            return True
    return False


@app.get("/api/settings")
def api_get_settings() -> dict:
    return default_settings()


@app.post("/api/settings")
def api_save_settings(req: SettingsRequest) -> dict:
    media = clean_path_value(req.media_root)
    output = clean_path_value(req.output_root or req.media_root)
    if not path_in_allowed_roots(Path(media)) or not path_in_allowed_roots(Path(output)):
        raise HTTPException(status_code=400, detail="Path is outside configured browse roots")
    language = req.language if req.language in {"en", "zh-CN"} else "zh-CN"
    source_dirs = ",".join(part.strip().strip("/") for part in req.source_dirs.split(",") if part.strip())
    monitor_dirs = ",".join(part.strip().strip("/") for part in req.monitor_dirs.split(",") if part.strip())
    try:
        interval_value = int(req.monitor_interval_minutes or 10)
    except (TypeError, ValueError):
        interval_value = 10
    interval = str(max(1, min(1440, interval_value)))
    save_settings({
        "media_root": media,
        "output_root": output,
        "source_dirs": source_dirs,
        "language": language,
        "monitor_enabled": "true" if req.monitor_enabled else "false",
        "monitor_dirs": monitor_dirs,
        "monitor_interval_minutes": interval,
    })
    return default_settings()


def monitor_target_dirs(settings: dict) -> list[Path]:
    media = Path(settings["media_root"])
    raw_dirs = settings.get("monitor_dirs") or settings.get("source_dirs") or ""
    parts = [part.strip() for part in raw_dirs.split(",") if part.strip()]
    if not parts:
        return []
    targets = []
    for part in parts:
        path = Path(part) if part.startswith("/") else media / part.strip("/")
        if path_in_allowed_roots(path):
            targets.append(path)
    return targets


def monitor_signature(settings: dict) -> str:
    import hashlib

    media_exts = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif"}
    digest = hashlib.sha256()
    count = 0
    total_size = 0
    latest_mtime = 0
    for target in monitor_target_dirs(settings):
        if not target.exists():
            continue
        for path in target.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in media_exts:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            count += 1
            total_size += stat.st_size
            latest_mtime = max(latest_mtime, int(stat.st_mtime))
            digest.update(str(path.relative_to(target)).encode("utf-8", "ignore"))
            digest.update(str(stat.st_size).encode())
            digest.update(str(int(stat.st_mtime)).encode())
    return f"{count}:{total_size}:{latest_mtime}:{digest.hexdigest()[:24]}"


def monitor_once() -> dict:
    settings = default_settings()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    if not settings.get("monitor_enabled"):
        save_settings({"monitor_last_checked_at": now})
        return {"enabled": False, "message": "disabled"}
    if not monitor_target_dirs(settings):
        save_settings({"monitor_last_checked_at": now})
        return {"enabled": True, "message": "no monitor dirs"}
    signature = monitor_signature(settings)
    previous = settings.get("monitor_last_signature", "")
    updates = {"monitor_last_checked_at": now}
    if not previous:
        updates["monitor_last_signature"] = signature
        save_settings(updates)
        return {"enabled": True, "changed": False, "message": "baseline saved", "signature": signature}
    if signature == previous:
        save_settings(updates)
        return {"enabled": True, "changed": False, "message": "no changes", "signature": signature}
    try:
        job_id = create_job("workflow-new-downloads")
    except RuntimeError as exc:
        save_settings(updates)
        return {"enabled": True, "changed": True, "queued": False, "message": str(exc), "signature": signature}
    updates["monitor_last_signature"] = signature
    updates["monitor_last_job_id"] = str(job_id)
    save_settings(updates)
    return {"enabled": True, "changed": True, "queued": True, "job_id": job_id, "signature": signature}


def monitor_loop() -> None:
    while True:
        settings = default_settings()
        interval = int(settings.get("monitor_interval_minutes") or 10)
        try:
            monitor_once()
        except Exception:
            pass
        time.sleep(max(60, interval * 60))


def start_monitor_thread() -> None:
    thread = threading.Thread(target=monitor_loop, daemon=True)
    thread.start()


@app.get("/api/monitor")
def api_monitor() -> dict:
    settings = default_settings()
    return {
        "enabled": settings.get("monitor_enabled"),
        "dirs": [str(path) for path in monitor_target_dirs(settings)],
        "interval_minutes": settings.get("monitor_interval_minutes"),
        "last_signature": settings.get("monitor_last_signature"),
        "last_job_id": settings.get("monitor_last_job_id"),
        "last_checked_at": settings.get("monitor_last_checked_at"),
    }


@app.post("/api/monitor/check")
def api_monitor_check(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(monitor_once)
    return {"queued": True}


@app.get("/api/directories")
def api_directories(path: str = Query("/media", max_length=500)) -> dict:
    target = Path(clean_path_value(path))
    if not path_in_allowed_roots(target):
        raise HTTPException(status_code=400, detail="Path is outside configured browse roots")
    rows = []
    if target.exists():
        for item in sorted(target.iterdir(), key=lambda p: p.name.lower()):
            if item.is_dir():
                rows.append({"name": item.name, "path": str(item), "readable": os.access(item, os.R_OK)})
    return {"path": str(target), "exists": target.exists(), "directories": rows}


@app.get("/api/search")
def api_search(
    q: str = Query("", max_length=200),
    source: str = Query("all"),
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    root = output_root()
    manifests = root / "_MANIFESTS"
    query = q.strip().lower()
    files = {
        "manifest": manifests / "manifest_all.csv",
        "move_plan": manifests / "move_plan.csv",
        "applied": manifests / "applied_moves.csv",
        "filename_words": manifests / "filename_words.csv",
        "filename_analysis": manifests / "filename_analysis.csv",
        "face_groups": manifests / "face_groups.csv",
        "face_report": manifests / "face_cluster_report.csv",
        "face_merge_suggestions": manifests / "face_merge_suggestions.csv",
        "vision_labels": manifests / "vision_labels.csv",
        "vision_move_plan": manifests / "vision_move_plan.csv",
        "organized_duplicates": manifests / "organized_duplicates.csv",
    }
    selected = files if source == "all" else {source: files[source]} if source in files else {}
    if not selected:
        raise HTTPException(status_code=400, detail="Unsupported search source")
    results = []
    for name, path in selected.items():
        for row in read_csv(path):
            haystack = " ".join(str(value) for value in row.values()).lower()
            if query and query not in haystack:
                continue
            item = {"source": name, **row}
            results.append(item)
            if len(results) >= limit:
                return {"query": q, "source": source, "limit": limit, "results": results}
    return {"query": q, "source": source, "limit": limit, "results": results}


@app.get("/api/media")
def api_media(
    q: str = Query("", max_length=200),
    media_type: str = Query("all"),
    tag: str = Query("", max_length=120),
    author: str = Query("", max_length=120),
    include_risk: bool = Query(False),
    limit: int = Query(80, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    return media_query(q=q.strip(), media_type=media_type, tag=tag.strip(), author=author.strip(), limit=limit, offset=offset, include_risk=include_risk)


@app.get("/api/risk")
def api_risk(limit: int = Query(100, ge=1, le=300)) -> dict:
    return risk_queue(limit=limit)


@app.post("/api/media/rebuild-index")
def api_rebuild_media_index() -> dict:
    return rebuild_metadata_index(output_root())


@app.post("/api/media/rebuild-similarity")
def api_rebuild_similarity() -> dict:
    return rebuild_similarity_index(output_root())


@app.get("/api/media/similarity-groups")
def api_similarity_groups(limit: int = Query(100, ge=1, le=300)) -> dict:
    return similarity_groups(limit=limit)


def checked_media_detail(media_id: int) -> dict:
    detail = media_detail(media_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Media not found")
    path = Path(detail["path"]).resolve()
    try:
        path.relative_to(output_root().resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Media path is outside library root") from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail="Media file missing")
    detail["path"] = str(path)
    return detail


@app.get("/api/media/{media_id}")
def api_media_detail(media_id: int) -> dict:
    return checked_media_detail(media_id)


@app.get("/api/media/{media_id}/file")
def api_media_file(media_id: int):
    detail = checked_media_detail(media_id)
    path = Path(detail["path"])
    return FileResponse(path, media_type=mime_for(path, detail.get("media_type", "")))


@app.get("/api/media/{media_id}/thumbnail")
def api_media_thumbnail(media_id: int):
    detail = checked_media_detail(media_id)
    path = Path(detail["path"])
    thumb_dir = output_root() / "_MANIFESTS" / "media_thumbs_v2"
    thumb = thumb_dir / f"{media_id}.jpg"
    if thumb.exists():
        return FileResponse(thumb, media_type="image/jpeg")
    thumb_dir.mkdir(parents=True, exist_ok=True)
    if detail.get("media_type") == "photo" and write_smart_thumbnail(path, thumb):
        return FileResponse(thumb, media_type="image/jpeg")
    if detail.get("media_type") == "video" and run_ffmpeg_thumbnail(path, thumb, width=800, timeout=30):
        return FileResponse(thumb, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Thumbnail not found")


@app.get("/api/logs")
def api_logs(limit: int = Query(20, ge=1, le=100)) -> dict:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return {"jobs": rows_to_dicts(rows)}


def record_manual_job(command: str, stdout: str, stderr: str = "", status: str = "done") -> int:
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO jobs (command, status, progress, message, started_at, finished_at, stdout, stderr)
            VALUES (?, ?, 100, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?, ?)
            """,
            (command, status, f"manual {command}", stdout[-20000:], stderr[-20000:]),
        )
        return int(cur.lastrowid)


def safe_actor_name(name: str) -> str:
    cleaned = name.replace("/", "_").replace("\\", "_").replace(":", "_").strip(" ._-")
    if not cleaned or cleaned in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid actor name")
    return cleaned[:80]


def actor_counts(actor_dir: Path) -> tuple[int, int]:
    photos = sum(1 for path in (actor_dir / "Photos").rglob("*") if path.is_file()) if (actor_dir / "Photos").exists() else 0
    videos = sum(1 for path in (actor_dir / "Videos").rglob("*") if path.is_file()) if (actor_dir / "Videos").exists() else 0
    return photos, videos


def actor_has_thumbnail(root: Path, actor: str) -> bool:
    actor_dir = root / "Actors" / actor
    photo_exts = {".jpg", ".jpeg", ".png", ".webp"}
    if (actor_dir / "Photos").exists() and any(path.is_file() and path.suffix.lower() in photo_exts for path in (actor_dir / "Photos").rglob("*")):
        return True
    cache = root / "_MANIFESTS" / "author_thumbs" / f"{actor}.jpg"
    return cache.exists()


@app.get("/api/authors")
def api_authors() -> list[dict]:
    root = output_root()
    actors_root = root / "Actors"
    aliases = read_csv(root / "_MANIFESTS" / "face_aliases.csv")
    face_counts: dict[str, int] = {}
    for row in aliases:
        actor = row.get("actor_name", "")
        if actor:
            face_counts[actor] = face_counts.get(actor, 0) + 1
    rows = []
    if actors_root.exists():
        for actor_dir in sorted([path for path in actors_root.iterdir() if path.is_dir()], key=lambda path: path.name.lower()):
            photos, videos = actor_counts(actor_dir)
            total = photos + videos
            if total == 0:
                continue
            rows.append({
                "name": actor_dir.name,
                "photos": photos,
                "videos": videos,
                "files": total,
                "face_groups": face_counts.get(actor_dir.name, 0),
                "has_thumbnail": actor_has_thumbnail(root, actor_dir.name),
                "thumbnail_url": f"/api/authors/{actor_dir.name}/thumbnail",
            })
    rows.sort(key=lambda row: (-int(row["files"]), row["name"]))
    return rows[:1000]


@app.get("/api/authors/{actor_name}/thumbnail")
def api_author_thumbnail(actor_name: str):
    root = output_root()
    actor = safe_actor_name(actor_name)
    actor_dir = (root / "Actors" / actor).resolve()
    try:
        actor_dir.relative_to((root / "Actors").resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid actor path") from exc
    photo_exts = {".jpg", ".jpeg", ".png", ".webp"}
    for base in [actor_dir / "Photos", actor_dir]:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix.lower() in photo_exts:
                media_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
                return FileResponse(path, media_type=media_type)

    thumb_dir = root / "_MANIFESTS" / "author_thumbs"
    thumb = thumb_dir / f"{actor}.jpg"
    if thumb.exists():
        return FileResponse(thumb, media_type="image/jpeg")
    video_exts = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm"}
    video_dir = actor_dir / "Videos"
    if video_dir.exists():
        for video in sorted(video_dir.rglob("*")):
            if not video.is_file() or video.suffix.lower() not in video_exts:
                continue
            thumb_dir.mkdir(parents=True, exist_ok=True)
            if run_ffmpeg_thumbnail(video, thumb, width=800, timeout=30):
                return FileResponse(thumb, media_type="image/jpeg")

    aliases = {row.get("face_group", ""): row.get("actor_name", "") for row in read_csv(root / "_MANIFESTS" / "face_aliases.csv")}
    groups = read_csv(root / "_MANIFESTS" / "face_groups.csv")
    for row in groups:
        if aliases.get(row.get("face_group", "")) != actor:
            continue
        rel_frame = row.get("representative_frame") or row.get("frame_path")
        if rel_frame:
            image_path = (root / rel_frame).resolve()
            try:
                image_path.relative_to(root.resolve())
            except ValueError:
                continue
            if image_path.exists():
                return FileResponse(image_path, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Thumbnail not found")


@app.post("/api/authors/rename")
def api_rename_actor(req: ActorRenameRequest) -> dict:
    old_name = safe_actor_name(req.old_name)
    new_name = safe_actor_name(req.new_name)
    proc = run_core_command(["rename-actor", old_name, new_name])
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=proc.stderr or proc.stdout)
    job_id = record_manual_job("rename-actor", f"{old_name} => {new_name}\n\n{proc.stdout}", proc.stderr)
    return {"ok": True, "stdout": proc.stdout, "job_id": job_id}


@app.post("/api/authors/exclude")
def api_exclude_actor(req: ActorExcludeRequest) -> dict:
    actor = safe_actor_name(req.actor_name)
    proc = run_core_command(["exclude-actor", actor])
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=proc.stderr or proc.stdout)
    job_id = record_manual_job("exclude-actor", f"actor_name={actor}\n\n{proc.stdout}", proc.stderr)
    return {"ok": True, "stdout": proc.stdout, "job_id": job_id}


@app.post("/api/authors/sync")
def api_sync_authors() -> dict:
    proc = run_core_command(["sync-authors"], timeout=300)
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=proc.stderr or proc.stdout)
    job_id = record_manual_job("sync-authors", proc.stdout, proc.stderr)
    return {"ok": True, "stdout": proc.stdout, "job_id": job_id}


@app.get("/api/face-groups")
def api_face_groups() -> list[dict]:
    root = output_root()
    report = root / "_MANIFESTS" / "face_cluster_report.csv"
    groups = root / "_MANIFESTS" / "face_groups.csv"
    rows = read_csv(report) or read_csv(groups)
    aliases = {row.get("face_group", ""): row.get("actor_name", "") for row in read_csv(root / "_MANIFESTS" / "face_aliases.csv")}
    enhanced = []
    seen = set()
    for row in rows:
        group = row.get("face_group", "")
        if not group or group in seen:
            continue
        seen.add(group)
        item = {**row}
        item["actor_name"] = aliases.get(group, "")
        item["thumbnail_url"] = f"/api/face-groups/{group}/thumbnail"
        enhanced.append(item)
        if len(enhanced) >= 500:
            break
    return enhanced


@app.get("/api/face-merge-suggestions")
def api_face_merge_suggestions() -> list[dict]:
    root = output_root()
    return read_csv(root / "_MANIFESTS" / "face_merge_suggestions.csv")[:500]


@app.get("/api/face-groups/{face_group}/thumbnail")
def api_face_group_thumbnail(face_group: str):
    if not face_group.startswith("FaceGroup_"):
        raise HTTPException(status_code=400, detail="Invalid face group")
    root = output_root()
    groups = root / "_MANIFESTS" / "face_groups.csv"
    for row in read_csv(groups):
        if row.get("face_group") != face_group:
            continue
        rel_frame = row.get("representative_frame") or row.get("frame_path")
        if not rel_frame:
            continue
        image_path = (root / rel_frame).resolve()
        try:
            image_path.relative_to(root.resolve())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid thumbnail path") from exc
        if image_path.exists():
            return FileResponse(image_path, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Thumbnail not found")


@app.post("/api/face-groups/name")
def api_name_face_group(req: FaceNameRequest) -> dict:
    if not req.face_group.startswith("FaceGroup_"):
        raise HTTPException(status_code=400, detail="Invalid face group")
    settings = default_settings()
    root = settings["media_root"]
    output = settings["output_root"]
    script = os.environ.get("CORE_SCRIPT", "/app/backend/core/tg_media_library.py")
    local_script = Path(__file__).resolve().parents[1] / "core" / "tg_media_library.py"
    if not Path(script).exists() and local_script.exists():
        script = str(local_script)
    proc = subprocess.run(
        ["python", script, "--root", root, "--output-root", output, "name-face-group", req.face_group, req.actor_name],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=proc.stderr or proc.stdout)
    job_id = record_manual_job(
        "name-face-group",
        f"face_group={req.face_group}\nactor_name={req.actor_name}\n\n{proc.stdout}",
        proc.stderr,
    )
    return {"ok": True, "stdout": proc.stdout, "job_id": job_id}


@app.post("/api/face-groups/merge")
def api_merge_face_group(req: FaceMergeRequest) -> dict:
    if not req.source_group.startswith("FaceGroup_") or not req.target_group.startswith("FaceGroup_"):
        raise HTTPException(status_code=400, detail="Invalid face group")
    if req.source_group == req.target_group:
        raise HTTPException(status_code=400, detail="Source and target are the same")
    settings = default_settings()
    script = os.environ.get("CORE_SCRIPT", "/app/backend/core/tg_media_library.py")
    local_script = Path(__file__).resolve().parents[1] / "core" / "tg_media_library.py"
    if not Path(script).exists() and local_script.exists():
        script = str(local_script)
    proc = subprocess.run(
        ["python", script, "--root", settings["media_root"], "--output-root", settings["output_root"], "merge-face-groups", req.source_group, req.target_group],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=proc.stderr or proc.stdout)
    job_id = record_manual_job(
        "merge-face-groups",
        f"source_group={req.source_group}\ntarget_group={req.target_group}\n\n{proc.stdout}",
        proc.stderr,
    )
    return {"ok": True, "stdout": proc.stdout, "job_id": job_id}


@app.post("/api/face-groups/merge-named")
def api_merge_named_face_groups(req: FaceMergeNamedRequest) -> dict:
    settings = default_settings()
    script = os.environ.get("CORE_SCRIPT", "/app/backend/core/tg_media_library.py")
    local_script = Path(__file__).resolve().parents[1] / "core" / "tg_media_library.py"
    if not Path(script).exists() and local_script.exists():
        script = str(local_script)
    args = ["python", script, "--root", settings["media_root"], "--output-root", settings["output_root"], "merge-named-face-groups"]
    if req.actor_name.strip():
        args.append(req.actor_name.strip())
    proc = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=proc.stderr or proc.stdout)
    job_id = record_manual_job(
        "merge-named-face-groups",
        f"actor_name={req.actor_name.strip() or '*'}\n\n{proc.stdout}",
        proc.stderr,
    )
    return {"ok": True, "stdout": proc.stdout, "job_id": job_id}


frontend_dir = Path(os.environ.get("FRONTEND_DIST", "/app/frontend/dist"))
if frontend_dir.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dir / "assets"), name="assets")


@app.get("/{path:path}")
def frontend(path: str):
    index = frontend_dir / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"message": "Frontend is not built", "media_root": os.environ.get("MEDIA_ROOT", "/media")}


@app.head("/{path:path}")
def frontend_head(path: str):
    index = frontend_dir / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"message": "Frontend is not built"}

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
from .jobs import ALLOWED_COMMANDS, create_job, mark_interrupted_jobs, request_job_cancel
from .media_stats import summary
from .metadata import (
    add_manual_media_tag,
    backfill_media_metadata,
    media_by_relative_paths,
    media_detail,
    media_index_diagnostics,
    media_for_author,
    media_query,
    mime_for,
    rebuild_metadata_index,
    rebuild_similarity_index,
    risk_queue,
    set_tag_feedback,
    set_manual_author,
    set_media_favorite,
    soft_delete_media,
    similarity_groups,
    subtitle_for_media,
    tag_graph,
    train_vision_calibrators,
    vision_calibrator_status,
)
from .model_manager import MODEL_REGISTRY, delete_model, model_catalog, sha256_setting_key, source_setting_key

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


class TagFeedbackRequest(BaseModel):
    tag: str
    category: str = ""
    verdict: str
    note: str = ""


class FavoriteRequest(BaseModel):
    favorite: bool = True


class ManualTagRequest(BaseModel):
    tag: str
    category: str = ""


class ManualAuthorRequest(BaseModel):
    author: str = ""


class SettingsRequest(BaseModel):
    media_root: str
    output_root: str = ""
    source_dirs: str = ""
    language: str = "zh-CN"
    compute_device: str = "auto"
    ffmpeg_hwaccel: str = "auto"
    openvino_device: str = "GPU"
    openclip_model: str = "ViT-L-14"
    openclip_pretrained: str = "laion2b_s32b_b82k"
    openclip_strong_model: str = "ViT-H-14"
    openclip_strong_pretrained: str = "laion2b_s32b_b79k"
    openclip_strong_threshold: float = 0.62
    openclip_strong_low_conf_only: bool = True
    face_providers: str = "OpenVINOExecutionProvider,CPUExecutionProvider"
    whisper_device: str = "cpu"
    asr_engine: str = "auto"
    transcript_engine: str = "auto"
    audio_tag_mode: str = "sensevoice-sample"
    audio_tag_sample_seconds: int = 30
    sensevoice_gguf_bin: str = "llama-sensevoice"
    sensevoice_gguf_model: str = "/models/sensevoice/SenseVoiceSmall.gguf"
    sensevoice_gguf_command: str = ""
    frame_workers: int = 1
    frames_per_video: int = 3
    frame_checkpoint_every: int = 100
    transcribe_max_seconds: int = 0
    monitor_enabled: bool = False
    monitor_dirs: str = ""
    monitor_interval_minutes: int = 10


class ModelSourceRequest(BaseModel):
    model_id: str
    url: str = ""
    sha256: str = ""


class ModelManifestRequest(BaseModel):
    url: str = ""


class AuthRequest(BaseModel):
    password: str


@app.on_event("startup")
def startup() -> None:
    init_db()
    mark_interrupted_jobs()
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
    if path.startswith("/api/auth") or path.startswith("/assets") or path in {"/api/health", "/api/version"}:
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


@app.get("/api/version")
def api_version() -> dict:
    app_version = os.environ.get("APP_SEMVER", "1.1.2").lstrip("v") or "1.1.2"
    build_commit = os.environ.get("APP_VERSION", "dev")
    build_time = os.environ.get("APP_BUILT_AT", "")
    return {
        "version": f"v{app_version}",
        "app_version": app_version,
        "build_commit": build_commit,
        "build_time": build_time,
        "image": os.environ.get("APP_IMAGE", ""),
        "built_at": build_time,
    }


@app.get("/api/system/hardware")
def api_system_hardware() -> dict:
    def run(args: list[str]) -> str:
        try:
            return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=8).stdout[-4000:]
        except Exception as exc:
            return repr(exc)

    settings = default_settings()
    return {
        "compute_device": settings.get("compute_device", "auto"),
        "ffmpeg_hwaccel": settings.get("ffmpeg_hwaccel") or os.environ.get("FFMPEG_HWACCEL", ""),
        "ffmpeg_hw_device": os.environ.get("FFMPEG_HW_DEVICE", ""),
        "face_providers": settings.get("face_providers") or os.environ.get("FACE_PROVIDERS", ""),
        "openvino_device": settings.get("openvino_device") or os.environ.get("OPENVINO_DEVICE", ""),
        "whisper_device": settings.get("whisper_device") or os.environ.get("WHISPER_DEVICE", ""),
        "dri_exists": Path("/dev/dri").exists(),
        "dri": run(["sh", "-lc", "ls -la /dev/dri 2>/dev/null || true"]),
        "ffmpeg_hwaccels": run(["ffmpeg", "-hide_banner", "-hwaccels"]),
        "vainfo": run(["sh", "-lc", "vainfo --display drm --device ${FFMPEG_HW_DEVICE:-/dev/dri/renderD128} 2>&1 | head -80 || true"]),
        "clinfo": run(["sh", "-lc", "clinfo 2>&1 | head -120 || true"]),
        "onnxruntime": run(["python", "-c", "import onnxruntime as ort; print('\\n'.join(ort.get_available_providers()))"]),
    }


@app.get("/api/summary")
def api_summary() -> dict:
    return summary()


@app.get("/api/diagnostics")
def api_diagnostics() -> dict:
    return media_index_diagnostics(output_root())


@app.post("/api/media/metadata-backfill")
def api_metadata_backfill(limit: int = Query(200, ge=1, le=5000)) -> dict:
    return backfill_media_metadata(output_root(), limit=limit)


JOB_SUMMARY_COLUMNS = """
    id, command, status, progress, message, created_at, started_at, finished_at,
    stage, current_item, processed, total, success_count, failed_count,
    skipped_count, cancel_requested, heartbeat_at
"""


@app.get("/api/jobs")
def api_jobs(limit: int = Query(120, ge=1, le=300), status: str = Query("", max_length=40)) -> list[dict]:
    allowed = {"queued", "running", "done", "failed", "cancelled"}
    with connect() as conn:
        if status in allowed:
            rows = conn.execute(
                f"SELECT {JOB_SUMMARY_COLUMNS} FROM jobs WHERE status=? ORDER BY id DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(f"SELECT {JOB_SUMMARY_COLUMNS} FROM jobs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return rows_to_dicts(rows)


@app.get("/api/jobs/{job_id}")
def api_job(job_id: int) -> dict:
    with connect() as conn:
        row = conn.execute(f"SELECT {JOB_SUMMARY_COLUMNS} FROM jobs WHERE id=?", (job_id,)).fetchone()
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


@app.post("/api/jobs/{job_id}/cancel")
def api_cancel_job(job_id: int) -> dict:
    try:
        request_job_cancel(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "id": job_id}


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


@app.get("/api/models")
def api_models() -> dict:
    return model_catalog()


@app.delete("/api/models/{model_id}")
def api_delete_model(model_id: str) -> dict:
    try:
        return delete_model(model_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/models/source")
def api_save_model_source(req: ModelSourceRequest) -> dict:
    spec = MODEL_REGISTRY.get(req.model_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Unknown model")
    if spec.get("kind") != "file":
        raise HTTPException(status_code=400, detail="Only direct file models can use custom source URLs")
    url = req.url.strip()
    sha256 = req.sha256.strip()
    if url and not (url.startswith("https://") or url.startswith("http://")):
        raise HTTPException(status_code=400, detail="Model URL must start with http:// or https://")
    if sha256 and (len(sha256) != 64 or any(char not in "0123456789abcdefABCDEF" for char in sha256)):
        raise HTTPException(status_code=400, detail="SHA256 must be a 64-character hex string")
    save_settings({
        source_setting_key(req.model_id): url,
        sha256_setting_key(req.model_id): sha256,
    })
    return model_catalog()


@app.post("/api/models/manifest-source")
def api_save_model_manifest_source(req: ModelManifestRequest) -> dict:
    url = req.url.strip()
    if url and not (url.startswith("https://") or url.startswith("http://")):
        raise HTTPException(status_code=400, detail="Manifest URL must start with http:// or https://")
    save_settings({"model_manifest_url": url})
    return model_catalog()


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
    settings = get_settings()
    mode = (settings.get("ffmpeg_hwaccel") or os.environ.get("FFMPEG_HWACCEL", "")).strip().lower()
    if mode in {"", "none", "false", "0", "off"}:
        return []
    device = settings.get("ffmpeg_hw_device") or os.environ.get("FFMPEG_HW_DEVICE", "/dev/dri/renderD128")
    if mode in {"vaapi", "auto"} and Path(device).exists():
        return ["-hwaccel", "vaapi", "-hwaccel_device", device]
    if mode == "qsv":
        return ["-hwaccel", "qsv"]
    return []


THUMB_SIZE = (900, 900)
MEDIA_THUMB_CACHE = "media_thumbs_v8"
THUMB_CACHE_HEADERS = {"Cache-Control": "public, max-age=2592000, immutable"}
THUMB_HEALTH_VERSION = "health-v2"
_FRAME_INDEX_CACHE: dict[str, object] = {"mtime": -1.0, "rows": {}}
_FRAME_INDEX_LOCK = threading.Lock()
_TAG_GRAPH_CACHE: dict[str, object] = {"expires": 0.0, "key": None, "data": None}
_TAG_GRAPH_LOCK = threading.Lock()


def thumbnail_health_marker(thumb: Path) -> Path:
    return thumb.with_name(f"{thumb.name}.ok")


def thumbnail_signature(thumb: Path) -> str:
    stat = thumb.stat()
    return f"{THUMB_HEALTH_VERSION}:{stat.st_size}:{stat.st_mtime_ns}"


def remove_thumbnail_health_marker(thumb: Path) -> None:
    try:
        thumbnail_health_marker(thumb).unlink()
    except OSError:
        pass


def mark_thumbnail_healthy(thumb: Path) -> None:
    try:
        marker = thumbnail_health_marker(thumb)
        marker.write_text(thumbnail_signature(thumb), encoding="utf-8")
    except OSError:
        pass


def cached_thumbnail_is_healthy(thumb: Path) -> bool:
    if not thumb.exists():
        remove_thumbnail_health_marker(thumb)
        return False
    marker = thumbnail_health_marker(thumb)
    try:
        if marker.exists() and marker.read_text(encoding="utf-8").strip() == thumbnail_signature(thumb):
            return True
    except OSError:
        pass
    if thumbnail_is_healthy(thumb):
        mark_thumbnail_healthy(thumb)
        return True
    remove_thumbnail_health_marker(thumb)
    return False


def frame_index_rows(root: Path) -> dict[str, dict]:
    path = root / "_MANIFESTS" / "frame_index.csv"
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return {}
    with _FRAME_INDEX_LOCK:
        if _FRAME_INDEX_CACHE.get("mtime") == mtime:
            return dict(_FRAME_INDEX_CACHE.get("rows") or {})
        rows = {row.get("media_path", ""): row for row in read_csv(path) if row.get("media_path")}
        _FRAME_INDEX_CACHE["mtime"] = mtime
        _FRAME_INDEX_CACHE["rows"] = rows
        return dict(rows)


def cached_media_record(media_id: int) -> dict:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT id, path, root, relative_path, filename, media_type, resolution, quality
            FROM media_items
            WHERE id=?
            """,
            (media_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Media not found")
    data = dict(row)
    root = Path(data.get("root") or output_root()).resolve()
    path = Path(data["path"]).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Media path is outside library root") from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail="Media file missing")
    data["path"] = str(path)
    data["root"] = str(root)
    return data


def frame_preview_paths(root: Path, relative_path: str) -> tuple[list[Path], Path | None]:
    row = frame_index_rows(root).get(relative_path, {})
    frames = []
    for item in (row.get("frames") or "").split("|"):
        if not item:
            continue
        frame = (root / item).resolve()
        try:
            frame.relative_to(root)
        except ValueError:
            continue
        if frame.exists():
            frames.append(frame)
    sheet = None
    sheet_rel = row.get("contact_sheet") or ""
    if sheet_rel:
        candidate = (root / sheet_rel).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            candidate = None
        if candidate and candidate.exists():
            sheet = candidate
    return frames, sheet


def trim_near_black_border(image):
    try:
        gray = ImageOps.grayscale(image)
        width, height = gray.size
        pixels = gray.load()

        def row_has_content(y: int) -> bool:
            values = [pixels[x, y] for x in range(width)]
            return max(values) > 34 or (sum(values) / max(1, width)) > 14

        def col_has_content(x: int) -> bool:
            values = [pixels[x, y] for y in range(height)]
            return max(values) > 34 or (sum(values) / max(1, height)) > 14

        top = next((y for y in range(height) if row_has_content(y)), 0)
        bottom = next((y for y in range(height - 1, -1, -1) if row_has_content(y)), height - 1) + 1
        left = next((x for x in range(width) if col_has_content(x)), 0)
        right = next((x for x in range(width - 1, -1, -1) if col_has_content(x)), width - 1) + 1
    except Exception:
        return image
    crop_width = max(1, right - left)
    crop_height = max(1, bottom - top)
    if crop_width < width * 0.12 or crop_height < height * 0.04:
        return image
    if crop_width * crop_height < width * height * 0.02:
        return image
    if (left, top, right, bottom) == (0, 0, width, height):
        return image
    return image.crop((left, top, right, bottom))


def trim_uniform_border(image):
    if ImageChops is None:
        return trim_near_black_border(image)
    try:
        bg = Image.new(image.mode, image.size, image.getpixel((0, 0)))
        diff = ImageChops.difference(image, bg)
        bbox = diff.getbbox()
    except Exception:
        return trim_near_black_border(image)
    if not bbox:
        return image
    left, top, right, bottom = bbox
    original_area = image.size[0] * image.size[1]
    cropped_area = max(1, right - left) * max(1, bottom - top)
    if (left, top, right, bottom) == (0, 0, image.size[0], image.size[1]):
        return trim_near_black_border(image)
    if cropped_area < original_area * 0.04:
        return trim_near_black_border(image)
    return trim_near_black_border(image.crop(bbox))


def thumbnail_content_score(src: Path) -> float:
    if Image is None or ImageOps is None:
        return 0.0
    try:
        with Image.open(src) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
            gray = ImageOps.grayscale(image)
            width, height = gray.size
            pixels = gray.load()
            rows = []
            cols = []
            for y in range(height):
                values = [pixels[x, y] for x in range(width)]
                if max(values) > 44 or (sum(values) / max(1, width)) > 18:
                    rows.append(y)
            for x in range(width):
                values = [pixels[x, y] for y in range(height)]
                if max(values) > 44 or (sum(values) / max(1, height)) > 18:
                    cols.append(x)
            if not rows or not cols:
                return 0.0
            crop_width = max(cols) - min(cols) + 1
            crop_height = max(rows) - min(rows) + 1
            area_ratio = (crop_width * crop_height) / max(1, width * height)
            height_ratio = crop_height / max(1, height)
            width_ratio = crop_width / max(1, width)
            aspect_penalty = 1.0
            aspect = crop_width / max(1, crop_height)
            if aspect > 5.5 or aspect < 0.18:
                aspect_penalty = 0.18
            if height_ratio < 0.22 or width_ratio < 0.22:
                aspect_penalty *= 0.22
            center_y = (min(rows) + max(rows)) / 2
            center_penalty = 1.0 - min(0.55, abs(center_y - height / 2) / max(1, height))
            return area_ratio * height_ratio * width_ratio * aspect_penalty * center_penalty
    except Exception:
        return 0.0


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
            green_dominant = sum(1 for r, g, b in pixels if g > 145 and g > r * 1.45 and g > b * 1.45) / total
            magenta_dominant = sum(1 for r, g, b in pixels if r > 145 and b > 145 and g < min(r, b) * 0.65) / total
            if green_dominant > 0.54 or magenta_dominant > 0.42:
                return False
            gray = ImageOps.grayscale(sample)
            extrema = gray.getextrema()
            if extrema[1] - extrema[0] < 8:
                return False
            rows = []
            pix = gray.load()
            sw, sh = gray.size
            for y in range(sh):
                values = [pix[x, y] for x in range(sw)]
                rows.append(sum(values) / max(1, sw))
            if len(rows) > 8:
                jumps = sum(1 for a, b in zip(rows, rows[1:]) if abs(a - b) > 48)
                if jumps / max(1, len(rows) - 1) > 0.28:
                    return False
            return True
    except Exception:
        return False


def write_smart_thumbnail(src: Path, dest: Path, trim_borders: bool = False) -> bool:
    if Image is None or ImageOps is None:
        return False
    try:
        with Image.open(src) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
            if trim_borders:
                image = trim_uniform_border(image)
            resampling = getattr(Image, "Resampling", Image).LANCZOS
            image.thumbnail(THUMB_SIZE, resampling)
            dest.parent.mkdir(parents=True, exist_ok=True)
            image.save(dest, "JPEG", quality=86, optimize=True)
        return thumbnail_is_healthy(dest)
    except Exception:
        return False


def ffprobe_duration(src: Path, timeout: int = 10) -> float:
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(src),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
        )
        return max(0.0, float(proc.stdout.strip() or "0"))
    except (ValueError, subprocess.SubprocessError, OSError):
        return 0.0


def thumbnail_seek_points(src: Path) -> list[float]:
    duration = ffprobe_duration(src)
    if duration >= 12:
        return sorted({2.0, min(duration - 1.0, duration * 0.18), min(duration - 1.0, duration * 0.38), min(duration - 1.0, duration * 0.62)})
    if duration >= 4:
        return [1.0, max(1.0, duration * 0.45), max(1.0, duration * 0.72)]
    return [0.2]


def run_ffmpeg_thumbnail(src: Path, dest: Path, width: int = 800, timeout: int = 30) -> bool:
    prefixes = []
    hw = ffmpeg_hw_prefix()
    if hw:
        prefixes.append(hw)
    prefixes.append([])
    seek_points = thumbnail_seek_points(src)
    candidates: list[tuple[float, Path]] = []
    for prefix in prefixes:
        for index, seek in enumerate(seek_points):
            tmp = dest.with_name(f".{dest.stem}.{index}.raw.jpg")
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
            cmd = [
                "ffmpeg",
                "-y",
                *prefix,
                "-ss",
                str(max(0.0, seek)),
                "-i",
                str(src),
                "-frames:v",
                "1",
                "-vf",
                f"scale='min({width},iw)':-2",
                "-q:v",
                "4",
                str(tmp),
            ]
            try:
                proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout)
            except (subprocess.SubprocessError, OSError):
                continue
            if proc.returncode == 0 and thumbnail_is_healthy(tmp):
                candidates.append((thumbnail_content_score(tmp), tmp))
        if candidates:
            break
    candidates.sort(key=lambda item: item[0], reverse=True)
    for _, tmp in candidates:
        if write_smart_thumbnail(tmp, dest, trim_borders=False):
            for _, cleanup in candidates:
                try:
                    cleanup.unlink()
                except OSError:
                    pass
            return True
    for _, cleanup in candidates:
        try:
            cleanup.unlink()
        except OSError:
            pass
    try:
        dest.unlink()
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
    def setting_int(key: str, env_key: str, default: int, low: int, high: int) -> int:
        try:
            value = int(settings.get(key) or os.environ.get(env_key, str(default)))
        except (TypeError, ValueError):
            value = default
        return max(low, min(high, value))
    return {
        "media_root": media,
        "output_root": output,
        "source_dirs": settings.get("source_dirs") or os.environ.get("MEDIA_SOURCE_DIRS", ""),
        "language": settings.get("language") or os.environ.get("APP_LANGUAGE", "zh-CN"),
        "compute_device": settings.get("compute_device") or os.environ.get("COMPUTE_DEVICE", "auto"),
        "ffmpeg_hwaccel": settings.get("ffmpeg_hwaccel") or os.environ.get("FFMPEG_HWACCEL", "auto"),
        "openvino_device": settings.get("openvino_device") or os.environ.get("OPENVINO_DEVICE", "GPU"),
        "openclip_model": settings.get("openclip_model") or os.environ.get("OPENCLIP_MODEL", "ViT-L-14"),
        "openclip_pretrained": settings.get("openclip_pretrained") or os.environ.get("OPENCLIP_PRETRAINED", "laion2b_s32b_b82k"),
        "openclip_strong_model": settings.get("openclip_strong_model") or os.environ.get("OPENCLIP_STRONG_MODEL", "ViT-H-14"),
        "openclip_strong_pretrained": settings.get("openclip_strong_pretrained") or os.environ.get("OPENCLIP_STRONG_PRETRAINED", "laion2b_s32b_b79k"),
        "openclip_strong_threshold": setting_int("openclip_strong_threshold_pct", "OPENCLIP_STRONG_THRESHOLD_PCT", 62, 1, 99) / 100,
        "openclip_strong_low_conf_only": (settings.get("openclip_strong_low_conf_only") or os.environ.get("OPENCLIP_STRONG_LOW_CONF_ONLY", "true")).lower() in {"1", "true", "yes", "on"},
        "face_providers": settings.get("face_providers") or os.environ.get("FACE_PROVIDERS", "OpenVINOExecutionProvider,CPUExecutionProvider"),
        "whisper_device": settings.get("whisper_device") or os.environ.get("WHISPER_DEVICE", "cpu"),
        "asr_engine": settings.get("asr_engine") or os.environ.get("ASR_ENGINE", "auto"),
        "transcript_engine": settings.get("transcript_engine") or os.environ.get("TRANSCRIPT_ENGINE", settings.get("asr_engine") or os.environ.get("ASR_ENGINE", "auto")),
        "audio_tag_mode": settings.get("audio_tag_mode") or os.environ.get("AUDIO_TAG_MODE", "sensevoice-sample"),
        "audio_tag_sample_seconds": setting_int("audio_tag_sample_seconds", "AUDIO_TAG_SAMPLE_SECONDS", 30, 0, 3600),
        "sensevoice_gguf_bin": settings.get("sensevoice_gguf_bin") or os.environ.get("SENSEVOICE_GGUF_BIN", "llama-sensevoice"),
        "sensevoice_gguf_model": settings.get("sensevoice_gguf_model") or os.environ.get("SENSEVOICE_GGUF_MODEL", "/models/sensevoice/SenseVoiceSmall.gguf"),
        "sensevoice_gguf_command": settings.get("sensevoice_gguf_command") or os.environ.get("SENSEVOICE_GGUF_COMMAND", ""),
        "frame_workers": setting_int("frame_workers", "FRAME_WORKERS", 1, 1, 16),
        "frames_per_video": setting_int("frames_per_video", "FRAMES_PER_VIDEO", 3, 1, 12),
        "frame_checkpoint_every": setting_int("frame_checkpoint_every", "FRAME_CHECKPOINT_EVERY", 100, 10, 1000),
        "transcribe_max_seconds": setting_int("transcribe_max_seconds", "TRANSCRIBE_MAX_SECONDS", 0, 0, 86400),
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
    compute_device = req.compute_device if req.compute_device in {"auto", "gpu", "cpu"} else "auto"
    ffmpeg_hwaccel = req.ffmpeg_hwaccel if req.ffmpeg_hwaccel in {"auto", "none", "vaapi", "qsv"} else "auto"
    openvino_device = req.openvino_device if req.openvino_device in {"AUTO", "GPU", "CPU"} else "GPU"
    openclip_model = (req.openclip_model or "ViT-L-14").strip()
    openclip_pretrained = (req.openclip_pretrained or "laion2b_s32b_b82k").strip()
    openclip_strong_model = (req.openclip_strong_model or "ViT-H-14").strip()
    openclip_strong_pretrained = (req.openclip_strong_pretrained or "laion2b_s32b_b79k").strip()
    try:
        openclip_strong_threshold = max(0.01, min(0.99, float(req.openclip_strong_threshold or 0.62)))
    except (TypeError, ValueError):
        openclip_strong_threshold = 0.62
    face_providers = req.face_providers if req.face_providers in {"OpenVINOExecutionProvider,CPUExecutionProvider", "CPUExecutionProvider"} else "OpenVINOExecutionProvider,CPUExecutionProvider"
    whisper_device = req.whisper_device if req.whisper_device in {"cpu", "cuda"} else "cpu"
    asr_engine = req.asr_engine if req.asr_engine in {"auto", "sensevoice-gguf", "sensevoice", "faster-whisper", "whisper"} else "auto"
    if asr_engine == "sensevoice":
        asr_engine = "sensevoice-gguf"
    if asr_engine == "whisper":
        asr_engine = "faster-whisper"
    transcript_engine = req.transcript_engine if req.transcript_engine in {"auto", "funasr-nano-onnx", "funasr-nano", "sensevoice-gguf", "sensevoice", "faster-whisper", "whisper"} else asr_engine
    if transcript_engine == "sensevoice":
        transcript_engine = "sensevoice-gguf"
    if transcript_engine == "whisper":
        transcript_engine = "faster-whisper"
    if transcript_engine == "funasr-nano":
        transcript_engine = "funasr-nano-onnx"
    audio_tag_mode = req.audio_tag_mode if req.audio_tag_mode in {"off", "sensevoice-sample", "sensevoice-full"} else "sensevoice-sample"
    sensevoice_gguf_bin = (req.sensevoice_gguf_bin or "llama-sensevoice").strip()
    sensevoice_gguf_model = (req.sensevoice_gguf_model or "/models/sensevoice/SenseVoiceSmall.gguf").strip()
    if sensevoice_gguf_model and not sensevoice_gguf_model.startswith("/"):
        raise HTTPException(status_code=400, detail="SenseVoice model path must be an absolute container path")
    sensevoice_gguf_command = (req.sensevoice_gguf_command or "").strip()
    def clamp_int(value, default: int, low: int, high: int) -> str:
        try:
            parsed = int(value or default)
        except (TypeError, ValueError):
            parsed = default
        return str(max(low, min(high, parsed)))
    frame_workers = clamp_int(req.frame_workers, 1, 1, 16)
    frames_per_video = clamp_int(req.frames_per_video, 3, 1, 12)
    frame_checkpoint_every = clamp_int(req.frame_checkpoint_every, 100, 10, 1000)
    transcribe_max_seconds = clamp_int(req.transcribe_max_seconds, 0, 0, 86400)
    audio_tag_sample_seconds = clamp_int(req.audio_tag_sample_seconds, 30, 0, 3600)
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
        "compute_device": compute_device,
        "ffmpeg_hwaccel": ffmpeg_hwaccel,
        "openvino_device": openvino_device,
        "openclip_model": openclip_model,
        "openclip_pretrained": openclip_pretrained,
        "openclip_strong_model": openclip_strong_model,
        "openclip_strong_pretrained": openclip_strong_pretrained,
        "openclip_strong_threshold": f"{openclip_strong_threshold:.2f}",
        "openclip_strong_threshold_pct": str(int(round(openclip_strong_threshold * 100))),
        "openclip_strong_low_conf_only": "true" if req.openclip_strong_low_conf_only else "false",
        "face_providers": face_providers,
        "whisper_device": whisper_device,
        "asr_engine": asr_engine,
        "transcript_engine": transcript_engine,
        "audio_tag_mode": audio_tag_mode,
        "audio_tag_sample_seconds": audio_tag_sample_seconds,
        "sensevoice_gguf_bin": sensevoice_gguf_bin,
        "sensevoice_gguf_model": sensevoice_gguf_model,
        "sensevoice_gguf_command": sensevoice_gguf_command,
        "frame_workers": frame_workers,
        "frames_per_video": frames_per_video,
        "frame_checkpoint_every": frame_checkpoint_every,
        "transcribe_max_seconds": transcribe_max_seconds,
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
    type_filter: str = Query("", alias="type"),
    tag: str = Query("", max_length=120),
    author: str = Query("", max_length=120),
    include_risk: bool = Query(False),
    randomize: bool = Query(False),
    seed: int = Query(0, ge=0),
    limit: int = Query(80, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    if media_type == "all" and type_filter in {"photo", "video"}:
        media_type = type_filter
    return media_query(q=q.strip(), media_type=media_type, tag=tag.strip(), author=author.strip(), limit=limit, offset=offset, include_risk=include_risk, randomize=randomize, random_seed=seed)


@app.get("/api/tags/graph")
def api_tag_graph(
    limit_nodes: int = Query(80, ge=5, le=180),
    limit_edges: int = Query(180, ge=0, le=500),
    min_edge: int = Query(2, ge=1, le=50),
) -> dict:
    key = (limit_nodes, limit_edges, min_edge)
    now = time.time()
    with _TAG_GRAPH_LOCK:
        if _TAG_GRAPH_CACHE.get("key") == key and float(_TAG_GRAPH_CACHE.get("expires") or 0) > now:
            return dict(_TAG_GRAPH_CACHE.get("data") or {})
    data = tag_graph(limit_nodes=limit_nodes, limit_edges=limit_edges, min_edge=min_edge)
    with _TAG_GRAPH_LOCK:
        _TAG_GRAPH_CACHE["key"] = key
        _TAG_GRAPH_CACHE["data"] = data
        _TAG_GRAPH_CACHE["expires"] = time.time() + 120
    return data


@app.get("/api/vision/calibrator/status")
def api_vision_calibrator_status() -> dict:
    return vision_calibrator_status(output_root())


@app.post("/api/vision/calibrator/train")
def api_train_vision_calibrator() -> dict:
    return train_vision_calibrators(output_root())


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


@app.post("/api/media/{media_id}/tag-feedback")
def api_media_tag_feedback(media_id: int, req: TagFeedbackRequest) -> dict:
    verdict = 1 if req.verdict in {"approve", "positive", "yes", "1", "true"} else -1
    try:
        return set_tag_feedback(media_id, req.tag, req.category, verdict, req.note)
    except KeyError:
        raise HTTPException(status_code=404, detail="Media not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/media/{media_id}/favorite")
def api_media_favorite(media_id: int, req: FavoriteRequest) -> dict:
    try:
        return set_media_favorite(media_id, req.favorite)
    except KeyError:
        raise HTTPException(status_code=404, detail="Media not found")


@app.post("/api/media/{media_id}/manual-tag")
def api_media_manual_tag(media_id: int, req: ManualTagRequest) -> dict:
    try:
        return add_manual_media_tag(media_id, req.tag, req.category)
    except KeyError:
        raise HTTPException(status_code=404, detail="Media not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/media/{media_id}/author")
def api_media_author(media_id: int, req: ManualAuthorRequest) -> dict:
    try:
        return set_manual_author(media_id, req.author)
    except KeyError:
        raise HTTPException(status_code=404, detail="Media not found")


@app.delete("/api/media/{media_id}")
def api_media_delete(media_id: int) -> dict:
    try:
        return soft_delete_media(media_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Media not found")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/media/{media_id}/file")
def api_media_file(media_id: int):
    detail = checked_media_detail(media_id)
    path = Path(detail["path"])
    return FileResponse(path, media_type=mime_for(path, detail.get("media_type", "")))


@app.get("/api/media/{media_id}/subtitles.vtt")
def api_media_subtitles(media_id: int, mode: str = Query("original", pattern="^(original|bilingual)$")):
    checked_media_detail(media_id)
    try:
        content, _ = subtitle_for_media(media_id, mode)
    except KeyError:
        raise HTTPException(status_code=404, detail="Media not found")
    if not content:
        raise HTTPException(status_code=404, detail="Subtitle not found")
    return Response(content=content, media_type="text/vtt; charset=utf-8", headers={"Cache-Control": "no-store"})


@app.get("/api/media/{media_id}/thumbnail")
def api_media_thumbnail(media_id: int):
    detail = cached_media_record(media_id)
    path = Path(detail["path"])
    root = Path(detail.get("root") or output_root()).resolve()
    thumb_dir = root / "_MANIFESTS" / MEDIA_THUMB_CACHE
    thumb = thumb_dir / f"{media_id}.jpg"
    if thumb.exists():
        if cached_thumbnail_is_healthy(thumb):
            return FileResponse(thumb, media_type="image/jpeg", headers=THUMB_CACHE_HEADERS)
        try:
            thumb.unlink()
        except OSError:
            pass
        remove_thumbnail_health_marker(thumb)
    thumb_dir.mkdir(parents=True, exist_ok=True)
    if detail.get("media_type") == "photo" and write_smart_thumbnail(path, thumb):
        mark_thumbnail_healthy(thumb)
        return FileResponse(thumb, media_type="image/jpeg", headers=THUMB_CACHE_HEADERS)
    frame_previews, _ = frame_preview_paths(root, str(detail.get("relative_path") or ""))
    for frame in frame_previews:
        if thumbnail_is_healthy(frame):
            return FileResponse(frame, media_type="image/jpeg", headers=THUMB_CACHE_HEADERS)
    if detail.get("media_type") == "video" and run_ffmpeg_thumbnail(path, thumb, width=800, timeout=30):
        mark_thumbnail_healthy(thumb)
        return FileResponse(thumb, media_type="image/jpeg", headers=THUMB_CACHE_HEADERS)
    raise HTTPException(status_code=404, detail="Thumbnail not found")


@app.post("/api/media/{media_id}/thumbnail/rebuild")
def api_media_thumbnail_rebuild(media_id: int) -> dict:
    detail = cached_media_record(media_id)
    path = Path(detail["path"])
    root = Path(detail.get("root") or output_root()).resolve()
    thumb = root / "_MANIFESTS" / MEDIA_THUMB_CACHE / f"{media_id}.jpg"
    remove_thumbnail_health_marker(thumb)
    try:
        thumb.unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not remove old thumbnail: {exc}") from exc
    thumb.parent.mkdir(parents=True, exist_ok=True)
    ok = False
    if detail.get("media_type") == "photo":
        ok = write_smart_thumbnail(path, thumb)
    elif detail.get("media_type") == "video":
        ok = run_ffmpeg_thumbnail(path, thumb, width=900, timeout=45)
    if not ok:
        raise HTTPException(status_code=500, detail="Could not rebuild a healthy thumbnail")
    mark_thumbnail_healthy(thumb)
    return {"ok": True, "id": media_id, "thumbnail": str(thumb.relative_to(root))}


@app.get("/api/media/{media_id}/contact-sheet")
def api_media_contact_sheet(media_id: int):
    detail = cached_media_record(media_id)
    root = Path(detail.get("root") or output_root()).resolve()
    _, sheet = frame_preview_paths(root, str(detail.get("relative_path") or ""))
    if sheet is None:
        raise HTTPException(status_code=404, detail="Contact sheet not found")
    return FileResponse(sheet, media_type="image/jpeg", headers=THUMB_CACHE_HEADERS)


@app.post("/api/media/{media_id}/contact-sheet/rebuild")
def api_media_contact_sheet_rebuild(media_id: int) -> dict:
    detail = cached_media_record(media_id)
    if detail.get("media_type") != "video":
        raise HTTPException(status_code=400, detail="Contact sheets are only available for videos")
    root = Path(detail.get("root") or output_root()).resolve()
    path = Path(detail["path"]).resolve()
    try:
        from backend.core.tg_media_library import Config, extract_one_media_frame_job, frame_cache_dir, media_cache_key
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Frame tools unavailable: {exc}") from exc

    import csv
    import shutil

    settings = get_settings()
    try:
        frames = int(settings.get("frames_per_video") or os.environ.get("FRAMES_PER_VIDEO", "3"))
    except (TypeError, ValueError):
        frames = 3
    frames = max(1, min(12, frames))
    config = Config(root=root, output_root=root)
    cache_dir = frame_cache_dir(config) / media_cache_key(path)
    try:
        shutil.rmtree(cache_dir)
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not clear old video overview cache: {exc}") from exc

    row = extract_one_media_frame_job(config, path, frames)
    if row.get("error") or not row.get("contact_sheet"):
        raise HTTPException(status_code=500, detail=row.get("error") or "Could not rebuild video overview")

    frame_index = root / "_MANIFESTS" / "frame_index.csv"
    frame_index.parent.mkdir(parents=True, exist_ok=True)
    rows = [item for item in read_csv(frame_index) if item.get("media_path") != row.get("media_path")]
    rows.append(row)
    fieldnames = ["media_path", "cache_key", "kind", "frames", "frame_times", "contact_sheet", "error"]
    with frame_index.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    _FRAME_INDEX_CACHE["mtime"] = 0.0
    _FRAME_INDEX_CACHE["rows"] = {}
    return {
        "ok": True,
        "id": media_id,
        "contact_sheet": row.get("contact_sheet"),
        "frames": len([item for item in (row.get("frames") or "").split("|") if item]),
    }


@app.get("/api/logs")
def api_logs(limit: int = Query(20, ge=1, le=100)) -> dict:
    with connect() as conn:
        rows = conn.execute(f"SELECT {JOB_SUMMARY_COLUMNS} FROM jobs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
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


@app.get("/api/authors/{actor_name}/media")
def api_author_media(
    actor_name: str,
    media_type: str = Query("all"),
    limit: int = Query(80, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    actor = safe_actor_name(actor_name)
    return media_for_author(actor, media_type=media_type, limit=limit, offset=offset)


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


@app.get("/api/face-groups/{face_group}/media")
def api_face_group_media(face_group: str, limit: int = Query(120, ge=1, le=300)) -> dict:
    if not face_group.startswith("FaceGroup_"):
        raise HTTPException(status_code=400, detail="Invalid face group")
    root = output_root()
    paths = []
    for row in read_csv(root / "_MANIFESTS" / "face_groups.csv"):
        if row.get("face_group") == face_group and row.get("media_path"):
            paths.append(row["media_path"])
    return media_by_relative_paths(root, sorted(set(paths)), limit=limit)


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
        return FileResponse(index, headers={"Cache-Control": "no-store, max-age=0"})
    return {"message": "Frontend is not built", "media_root": os.environ.get("MEDIA_ROOT", "/media")}


@app.head("/{path:path}")
def frontend_head(path: str):
    index = frontend_dir / "index.html"
    if index.exists():
        return FileResponse(index, headers={"Cache-Control": "no-store, max-age=0"})
    return {"message": "Frontend is not built"}

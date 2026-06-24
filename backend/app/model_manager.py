from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory

from .db import get_settings


def model_root() -> Path:
    return Path(os.environ.get("MODEL_ROOT", "/models"))


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


MODEL_REGISTRY = {
    "openclip-vit-l": {
        "name": "OpenCLIP ViT-L-14",
        "category": "vision",
        "kind": "runtime-cache",
        "description": "Default local scene, clothing, style, and content tag model.",
        "description_zh": "默认本地画面标签模型，用于场景、服装风格、拍摄方式和内容类型识别。",
        "path": "torch",
        "command": "openclip",
        "model": "ViT-L-14",
        "pretrained": "laion2b_s32b_b82k",
        "recommended": True,
    },
    "openclip-vit-h": {
        "name": "OpenCLIP ViT-H-14",
        "category": "vision",
        "kind": "runtime-cache",
        "description": "Stronger low-confidence rescan model. Larger and slower.",
        "description_zh": "更强的低置信度复扫模型，体积更大、速度更慢，适合二次精修标签。",
        "path": "torch",
        "command": "openclip",
        "model": "ViT-H-14",
        "pretrained": "laion2b_s32b_b79k",
        "recommended": False,
    },
    "insightface-buffalo-l": {
        "name": "InsightFace buffalo_l",
        "category": "face",
        "kind": "runtime-cache",
        "description": "Local face detection and same-face embedding model.",
        "description_zh": "本地人脸检测和同脸聚类模型，只做相似脸分组，不推断真实身份。",
        "path": "insightface/models/buffalo_l",
        "command": "insightface",
        "recommended": True,
    },
    "faster-whisper-small": {
        "name": "faster-whisper small",
        "category": "speech",
        "kind": "runtime-cache",
        "description": "Fallback speech-to-text model when SenseVoice GGUF is unavailable.",
        "description_zh": "SenseVoice 不可用时的备用语音转文字模型。",
        "path": "whisper",
        "command": "faster-whisper",
        "model": "small",
        "recommended": False,
    },
    "sensevoice-small-gguf": {
        "name": "SenseVoice Small GGUF",
        "category": "speech",
        "kind": "file",
        "description": "Preferred full-video speech recognition model for Mandarin/Japanese mixed media.",
        "description_zh": "推荐的完整视频语音识别模型，适合中文、日文和混合语音素材。",
        "path": "sensevoice/SenseVoiceSmall.gguf",
        "official_url": "https://huggingface.co/FunAudioLLM/SenseVoiceSmall-GGUF",
        "default_url": "https://huggingface.co/FunAudioLLM/SenseVoiceSmall-GGUF/resolve/main/sensevoice-small.gguf",
        "url_env": "SENSEVOICE_GGUF_URL",
        "sha256_env": "SENSEVOICE_GGUF_SHA256",
        "recommended": True,
    },
    "sensevoice-fsmn-vad-gguf": {
        "name": "FSMN VAD GGUF",
        "category": "speech",
        "kind": "file",
        "description": "Voice activity detection model required by the FunASR llama.cpp SenseVoice runtime.",
        "description_zh": "FunASR llama.cpp SenseVoice 运行时需要的语音活动检测模型。",
        "path": "sensevoice/fsmn-vad.gguf",
        "official_url": "https://huggingface.co/FunAudioLLM/fsmn-vad-GGUF",
        "default_url": "https://huggingface.co/FunAudioLLM/fsmn-vad-GGUF/resolve/main/fsmn-vad.gguf",
        "url_env": "SENSEVOICE_VAD_GGUF_URL",
        "sha256_env": "SENSEVOICE_VAD_GGUF_SHA256",
        "recommended": True,
    },
    "sensevoice-llamacpp-runtime": {
        "name": "FunASR llama.cpp runtime",
        "category": "speech",
        "kind": "archive",
        "description": "Linux x64 command-line runtime for SenseVoice GGUF transcription.",
        "description_zh": "SenseVoice GGUF 转写所需的 Linux x64 命令行运行时。",
        "path": "sensevoice/bin/llama-funasr-sensevoice",
        "archive_member": "llama-funasr-sensevoice",
        "official_url": "https://github.com/FunAudioLLM/SenseVoice/releases/tag/runtime-llamacpp-v0.1.2",
        "default_url": "https://github.com/FunAudioLLM/SenseVoice/releases/download/runtime-llamacpp-v0.1.2/funasr-llamacpp-linux-x64.tar.gz",
        "url_env": "SENSEVOICE_RUNTIME_URL",
        "sha256_env": "SENSEVOICE_RUNTIME_SHA256",
        "recommended": True,
    },
    "custom-detector-onnx": {
        "name": "Custom detector ONNX",
        "category": "vision",
        "kind": "file",
        "description": "Optional future clothing/scene detector exported from your own labeled data.",
        "description_zh": "可选自训练画面检测模型，可由你后续标注数据导出，用于更贴合个人素材库的分类。",
        "path": "detectors/custom.onnx",
        "official_url": "",
        "url_env": "CUSTOM_DETECTOR_ONNX_URL",
        "sha256_env": "CUSTOM_DETECTOR_ONNX_SHA256",
        "recommended": False,
    },
}


def _safe_path(relative: str) -> Path:
    root = model_root().resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Model path escapes MODEL_ROOT")
    return path


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for item in path.rglob("*"):
        try:
            if item.is_file():
                total += item.stat().st_size
        except OSError:
            pass
    return total


def _is_present(path: Path, kind: str) -> bool:
    if kind == "file":
        return path.is_file() and path.stat().st_size > 0
    if not path.exists():
        return False
    if path.is_file():
        return path.stat().st_size > 0
    return any(path.iterdir())


def _marker_path(model_id: str) -> Path:
    return _safe_path(f".tgmm-models/{model_id}.ready")


def source_setting_key(model_id: str) -> str:
    return f"model_url_{model_id}"


def sha256_setting_key(model_id: str) -> str:
    return f"model_sha256_{model_id}"


def _configured_url(model_id: str, spec: dict, settings: dict | None = None) -> str:
    settings = settings if settings is not None else get_settings()
    return (
        settings.get(source_setting_key(model_id), "").strip()
        or _env(str(spec.get("url_env", "")))
        or str(spec.get("default_url", "")).strip()
    )


def _configured_url_source(model_id: str, spec: dict, settings: dict | None = None) -> str:
    settings = settings if settings is not None else get_settings()
    if settings.get(source_setting_key(model_id), "").strip():
        return "settings"
    if _env(str(spec.get("url_env", ""))):
        return "env"
    if str(spec.get("default_url", "")).strip():
        return "default"
    return ""


def _configured_sha256(model_id: str, spec: dict, settings: dict | None = None) -> str:
    settings = settings if settings is not None else get_settings()
    return (
        settings.get(sha256_setting_key(model_id), "").strip()
        or _env(str(spec.get("sha256_env", "")))
        or str(spec.get("sha256", "")).strip()
    )


def _model_status(model_id: str, spec: dict) -> dict:
    settings = get_settings()
    path = _safe_path(str(spec["path"]))
    downloadable = spec.get("kind") in {"file", "archive"}
    url = _configured_url(model_id, spec, settings) if downloadable else ""
    url_source = _configured_url_source(model_id, spec, settings) if downloadable else ""
    sha256 = _configured_sha256(model_id, spec, settings) if downloadable else ""
    present = _is_present(path, str(spec["kind"]))
    if spec["kind"] == "runtime-cache" and spec.get("command") in {"openclip", "faster-whisper"}:
        present = _marker_path(model_id).exists()
    status = "ready" if present else ("needs_url" if downloadable and not url else "missing")
    return {
        "id": model_id,
        "name": spec["name"],
        "category": spec["category"],
        "kind": spec["kind"],
        "description": spec["description"],
        "description_zh": spec.get("description_zh", ""),
        "recommended": bool(spec.get("recommended")),
        "path": str(path),
        "status": status,
        "present": present,
        "bytes": _dir_size(path),
        "url_env": spec.get("url_env", ""),
        "url_configured": bool(url),
        "url_source": url_source,
        "source_url": url,
        "source_editable": downloadable,
        "official_url": spec.get("official_url", ""),
        "sha256_env": spec.get("sha256_env", ""),
        "sha256": sha256,
    }


def model_catalog() -> dict:
    root = model_root()
    settings = get_settings()
    return {
        "root": str(root),
        "manifest_url": settings.get("model_manifest_url", "").strip() or _env("MODEL_MANIFEST_URL"),
        "models": [_model_status(model_id, spec) for model_id, spec in MODEL_REGISTRY.items()],
    }


def delete_model(model_id: str) -> dict:
    spec = MODEL_REGISTRY.get(model_id)
    if not spec:
        raise ValueError("Unknown model")
    path = _safe_path(str(spec["path"]))
    marker = _marker_path(model_id)
    if spec["kind"] == "runtime-cache" and spec.get("command") in {"openclip", "faster-whisper"}:
        deleted = False
        if marker.exists():
            marker.unlink()
            deleted = True
        return {"ok": True, "deleted": deleted, "path": str(path), "note": "shared runtime cache kept; readiness marker removed"}
    if not path.exists():
        return {"ok": True, "deleted": False, "path": str(path)}
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    if marker.exists():
        marker.unlink()
    return {"ok": True, "deleted": True, "path": str(path)}


def _progress(stage: str, processed: int, total: int, current: str = "") -> None:
    pct = int(processed / total * 100) if total else 0
    print(
        "TGMM_PROGRESS "
        + json.dumps(
            {
                "stage": stage,
                "processed": processed,
                "total": total,
                "progress": max(0, min(99, pct)),
                "current": current,
                "message": f"{stage}: {processed}/{total}",
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


def _cancelled() -> bool:
    cancel = os.environ.get("TGMM_CANCEL_FILE", "")
    return bool(cancel and Path(cancel).exists())


def _verify_sha256(path: Path, expected: str) -> None:
    if not expected:
        return
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual.lower() != expected.lower():
        raise RuntimeError(f"sha256 mismatch for {path.name}: expected {expected}, got {actual}")


def _download_file(model_id: str, spec: dict) -> dict:
    settings = get_settings()
    url = _configured_url(model_id, spec, settings)
    if not url:
        raise RuntimeError(f"No source URL configured for {model_id}; set it in the Web Models page, then pull again")
    path = _safe_path(str(spec["path"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "tg-media-manager/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response, part.open("wb") as fh:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        last_emit = 0.0
        while True:
            if _cancelled():
                raise KeyboardInterrupt("cancelled")
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            fh.write(chunk)
            done += len(chunk)
            now = time.time()
            if total and now - last_emit > 1:
                _progress("model-download", done, total, path.name)
                last_emit = now
    _verify_sha256(part, _configured_sha256(model_id, spec, settings))
    part.replace(path)
    _progress("model-download", 1, 1, path.name)
    return {"ok": True, "model": model_id, "path": str(path), "bytes": path.stat().st_size}


def _download_archive(model_id: str, spec: dict) -> dict:
    settings = get_settings()
    url = _configured_url(model_id, spec, settings)
    if not url:
        raise RuntimeError(f"No source URL configured for {model_id}; set it in the Web Models page, then pull again")
    path = _safe_path(str(spec["path"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    member_name = str(spec.get("archive_member") or path.name)
    with TemporaryDirectory(prefix="tgmm_model_") as tmpdir:
        archive = Path(tmpdir) / "model-archive.tar.gz"
        req = urllib.request.Request(url, headers={"User-Agent": "tg-media-manager/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response, archive.open("wb") as fh:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            last_emit = 0.0
            while True:
                if _cancelled():
                    raise KeyboardInterrupt("cancelled")
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                fh.write(chunk)
                done += len(chunk)
                now = time.time()
                if total and now - last_emit > 1:
                    _progress("model-download", done, total, archive.name)
                    last_emit = now
        _verify_sha256(archive, _configured_sha256(model_id, spec, settings))
        with tarfile.open(archive, "r:gz") as tar:
            selected = None
            for member in tar.getmembers():
                if Path(member.name).name == member_name and member.isfile():
                    selected = member
                    break
            if selected is None:
                raise RuntimeError(f"{member_name} not found in {url}")
            extracted = tar.extractfile(selected)
            if extracted is None:
                raise RuntimeError(f"Unable to extract {member_name}")
            part = path.with_suffix(path.suffix + ".part")
            with part.open("wb") as fh:
                shutil.copyfileobj(extracted, fh)
            part.chmod(0o755)
            part.replace(path)
    _progress("model-download", 1, 1, path.name)
    return {"ok": True, "model": model_id, "path": str(path), "bytes": path.stat().st_size}


def _run_cache_command(model_id: str, spec: dict) -> dict:
    root = model_root()
    root.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.setdefault("MODEL_ROOT", str(root))
    env.setdefault("TORCH_HOME", str(root / "torch"))
    env.setdefault("HF_HOME", str(root / "huggingface"))
    env.setdefault("XDG_CACHE_HOME", str(root / "cache"))
    env.setdefault("INSIGHTFACE_HOME", str(root / "insightface"))
    command = spec["command"]
    if command == "openclip":
        code = (
            "import open_clip\n"
            f"print('downloading {spec['model']} {spec['pretrained']}', flush=True)\n"
            f"open_clip.create_model_and_transforms({spec['model']!r}, pretrained={spec['pretrained']!r}, device='cpu')\n"
            "print('ok', flush=True)\n"
        )
    elif command == "insightface":
        code = (
            "from insightface.app import FaceAnalysis\n"
            "import os\n"
            "root=os.environ.get('INSIGHTFACE_HOME','/models/insightface')\n"
            "print('downloading insightface buffalo_l', flush=True)\n"
            "app=FaceAnalysis(name='buffalo_l', root=root, providers=['CPUExecutionProvider'])\n"
            "app.prepare(ctx_id=-1, det_size=(640,640))\n"
            "print('ok', flush=True)\n"
        )
    elif command == "faster-whisper":
        code = (
            "from faster_whisper import WhisperModel\n"
            "import os\n"
            "root=os.path.join(os.environ.get('MODEL_ROOT','/models'),'whisper')\n"
            f"print('downloading faster-whisper {spec['model']}', flush=True)\n"
            f"WhisperModel({spec['model']!r}, device='cpu', compute_type='int8', download_root=root)\n"
            "print('ok', flush=True)\n"
        )
    else:
        raise RuntimeError(f"Unsupported model cache command: {command}")
    _progress("model-download", 0, 1, model_id)
    proc = subprocess.run([sys.executable, "-u", "-c", code], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=3600)
    print(proc.stdout, end="", flush=True)
    if proc.returncode != 0:
        print(proc.stderr, end="", flush=True)
        raise RuntimeError(f"{model_id} download failed with exit {proc.returncode}")
    marker = _marker_path(model_id)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"model": model_id, "created_at": time.time()}, ensure_ascii=False), encoding="utf-8")
    _progress("model-download", 1, 1, model_id)
    return {"ok": True, "model": model_id, "path": str(_safe_path(str(spec["path"]))), "stdout": proc.stdout[-4000:]}


def pull_model(model_id: str) -> dict:
    spec = MODEL_REGISTRY.get(model_id)
    if not spec:
        raise ValueError("Unknown model")
    if spec["kind"] == "file":
        return _download_file(model_id, spec)
    if spec["kind"] == "archive":
        return _download_archive(model_id, spec)
    return _run_cache_command(model_id, spec)

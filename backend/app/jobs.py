from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path

from .db import connect, get_settings
from .metadata import import_vision_outputs, rebuild_metadata_index, rebuild_similarity_index, transcribe_videos


ALLOWED_COMMANDS = {
    "workflow-new-downloads": [["scan"], ["analyze-filenames"], ["classify-keywords"], ["apply"], ["refresh-state"], ["__metadata_index__"]],
    "workflow-review-cleanup": [["normalize-organized"], ["classify-keywords"], ["organize-review"], ["refresh-state"], ["__metadata_index__"]],
    "workflow-face-balanced": [["extract-frames"], ["face-scan"], ["face-cluster", "--threshold", "0.80"], ["face-cluster-report"], ["apply-face-groups"]],
    "workflow-vision-plan": [["extract-frames"], ["vision-scan"], ["__vision_index__"], ["apply-vision-labels"]],
    "workflow-transcribe-sample": [["__transcribe_sample__"], ["__metadata_index__"]],
    "scan": ["scan"],
    "analyze-filenames": ["analyze-filenames"],
    "classify-keywords": ["classify-keywords"],
    "organize-review": ["organize-review"],
    "normalize-organized": ["normalize-organized"],
    "refresh-state": ["refresh-state"],
    "apply": ["apply"],
    "apply-include-review": ["apply", "--include-review"],
    "clean-empty-dirs": ["clean-empty-dirs"],
    "dedupe-organized-dry-run": ["dedupe-organized"],
    "dedupe-organized": ["dedupe-organized", "--apply"],
    "extract-frames-sample": ["extract-frames", "--limit", "120"],
    "extract-frames": ["extract-frames"],
    "face-setup": ["face-setup"],
    "face-scan-sample": ["face-scan", "--limit", "120"],
    "face-scan": ["face-scan"],
    "vision-scan-sample": ["vision-scan", "--limit", "120"],
    "vision-scan": ["vision-scan"],
    "index-vision": ["__vision_index__"],
    "face-cluster": ["face-cluster", "--threshold", "0.75"],
    "face-cluster-balanced": ["face-cluster", "--threshold", "0.80"],
    "face-cluster-relaxed": ["face-cluster", "--threshold", "0.90"],
    "face-cluster-report": ["face-cluster-report"],
    "apply-face-groups-dry-run": ["apply-face-groups"],
    "apply-face-groups": ["apply-face-groups", "--apply"],
    "apply-vision-labels-dry-run": ["apply-vision-labels"],
    "apply-vision-labels": ["apply-vision-labels", "--apply"],
    "index-metadata": ["__metadata_index__"],
    "index-similarity": ["__similarity_index__"],
    "transcribe-sample": ["__transcribe_sample__"],
    "transcribe": ["__transcribe__"],
}


def core_script() -> Path:
    configured = os.environ.get("CORE_SCRIPT")
    if configured:
        return Path(configured)
    container_path = Path("/app/backend/core/tg_media_library.py")
    if container_path.exists():
        return container_path
    return Path(__file__).resolve().parents[1] / "core" / "tg_media_library.py"


def create_job(command: str) -> int:
    if command not in ALLOWED_COMMANDS:
        raise ValueError(f"Unsupported command: {command}")
    with connect() as conn:
        active = conn.execute("SELECT id, command, status FROM jobs WHERE status IN ('queued', 'running') ORDER BY id DESC LIMIT 1").fetchone()
        if active is not None:
            raise RuntimeError(f"Job #{active['id']} ({active['command']}) is still {active['status']}")
        cur = conn.execute("INSERT INTO jobs (command, status, message) VALUES (?, 'queued', '')", (command,))
        job_id = int(cur.lastrowid)
    thread = threading.Thread(target=run_job, args=(job_id, command), daemon=True)
    thread.start()
    return job_id


def hardware_env(settings: dict) -> dict[str, str]:
    env = os.environ.copy()
    compute = (settings.get("compute_device") or os.environ.get("COMPUTE_DEVICE", "auto")).lower()
    ffmpeg = settings.get("ffmpeg_hwaccel") or os.environ.get("FFMPEG_HWACCEL", "auto")
    face = settings.get("face_providers") or os.environ.get("FACE_PROVIDERS", "")
    openvino = settings.get("openvino_device") or os.environ.get("OPENVINO_DEVICE", "")
    whisper = settings.get("whisper_device") or os.environ.get("WHISPER_DEVICE", "cpu")
    if compute == "cpu":
        ffmpeg = "none"
        face = "CPUExecutionProvider"
        openvino = "CPU"
        whisper = "cpu"
    elif compute == "gpu":
        ffmpeg = ffmpeg if ffmpeg != "none" else "auto"
        face = face or "OpenVINOExecutionProvider,CPUExecutionProvider"
        openvino = openvino or "GPU"
    env["COMPUTE_DEVICE"] = compute
    env["FFMPEG_HWACCEL"] = ffmpeg
    env["FACE_PROVIDERS"] = face or "OpenVINOExecutionProvider,CPUExecutionProvider"
    env["OPENVINO_DEVICE"] = openvino or "GPU"
    env["WHISPER_DEVICE"] = whisper
    env.setdefault("WHISPER_COMPUTE_TYPE", "int8")
    return env


def run_job(job_id: int, command: str) -> None:
    settings = get_settings()
    media_root = settings.get("media_root") or os.environ.get("MEDIA_ROOT", "/media")
    output_root = settings.get("output_root") or os.environ.get("MEDIA_OUTPUT_ROOT") or media_root
    source_dirs = settings.get("source_dirs") or os.environ.get("MEDIA_SOURCE_DIRS", "")
    steps = ALLOWED_COMMANDS[command]
    if steps and isinstance(steps[0], str):
        steps = [steps]
    base_args = ["python", str(core_script()), "--root", media_root, "--output-root", output_root]
    env = hardware_env(settings)
    os.environ.update({key: value for key, value in env.items() if key in {"COMPUTE_DEVICE", "FFMPEG_HWACCEL", "FACE_PROVIDERS", "OPENVINO_DEVICE", "WHISPER_DEVICE", "WHISPER_COMPUTE_TYPE"}})
    if source_dirs:
        base_args.extend(["--source-dirs", source_dirs])
    with connect() as conn:
        message = " && ".join(
            "index-metadata" if step == ["__metadata_index__"] else
            "index-vision" if step == ["__vision_index__"] else
            "index-similarity" if step == ["__similarity_index__"] else
            "transcribe-sample" if step == ["__transcribe_sample__"] else
            "transcribe" if step == ["__transcribe__"] else
            " ".join([*base_args, *step])
            for step in steps
        )
        conn.execute("UPDATE jobs SET status='running', started_at=CURRENT_TIMESTAMP, message=? WHERE id=?", (message, job_id))
    try:
        stdout_parts = []
        stderr_parts = []
        returncode = 0
        for step in steps:
            if step == ["__metadata_index__"]:
                result = rebuild_metadata_index(Path(output_root))
                stdout_parts.append(f"$ index-metadata\n{result}")
                returncode = 0
            elif step == ["__vision_index__"]:
                result = import_vision_outputs(Path(output_root))
                stdout_parts.append(f"$ index-vision\n{result}")
                returncode = 0
            elif step == ["__similarity_index__"]:
                result = rebuild_similarity_index(Path(output_root))
                stdout_parts.append(f"$ index-similarity\n{result}")
                returncode = 0
            elif step == ["__transcribe_sample__"]:
                result = transcribe_videos(Path(output_root), limit=5)
                stdout_parts.append(f"$ transcribe-sample\n{result}")
                returncode = 0 if result.get("ok") else 1
            elif step == ["__transcribe__"]:
                result = transcribe_videos(Path(output_root), limit=200)
                stdout_parts.append(f"$ transcribe\n{result}")
                returncode = 0 if result.get("ok") else 1
            else:
                step_args = [*base_args, *step]
                proc = subprocess.run(step_args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=None, env=env)
                stdout_parts.append(f"$ {' '.join(step_args)}\n{proc.stdout}")
                if proc.stderr:
                    stderr_parts.append(f"$ {' '.join(step_args)}\n{proc.stderr}")
                returncode = proc.returncode
                if proc.returncode != 0:
                    break
        status = "done" if returncode == 0 else "failed"
        with connect() as conn:
            conn.execute(
                "UPDATE jobs SET status=?, progress=100, finished_at=CURRENT_TIMESTAMP, stdout=?, stderr=?, message=? WHERE id=?",
                (status, "\n".join(stdout_parts)[-20000:], "\n".join(stderr_parts)[-20000:], f"exit {returncode}", job_id),
            )
    except Exception as exc:
        with connect() as conn:
            conn.execute(
                "UPDATE jobs SET status='failed', finished_at=CURRENT_TIMESTAMP, stderr=?, message=? WHERE id=?",
                (repr(exc), "exception", job_id),
            )

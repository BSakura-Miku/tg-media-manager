from __future__ import annotations

import os
import json
import signal
import select
import subprocess
import sys
import threading
import time
from contextlib import redirect_stdout
from pathlib import Path

from .db import connect, get_settings
from .metadata import backfill_media_metadata, import_vision_outputs, rebuild_metadata_index, rebuild_semantic_index, rebuild_similarity_index, train_vision_calibrators, transcribe_videos
from .model_manager import pull_model
from .thumbnail_tools import repair_thumbnail_cache


ALLOWED_COMMANDS = {
    "workflow-new-downloads": [["scan"], ["analyze-filenames"], ["classify-keywords"], ["apply"], ["refresh-state"], ["__metadata_index__"]],
    "workflow-review-cleanup": [["normalize-organized"], ["classify-keywords"], ["organize-review"], ["refresh-state"], ["__metadata_index__"]],
    "workflow-face-balanced": [["extract-frames"], ["face-scan"], ["face-cluster", "--threshold", "0.80"], ["face-cluster-report"], ["apply-face-groups"]],
    "workflow-vision-plan": [["extract-frames"], ["vision-scan"], ["__vision_index__"], ["apply-vision-labels"]],
    "workflow-full-library": [["scan"], ["analyze-filenames"], ["classify-keywords"], ["apply"], ["normalize-organized"], ["organize-review"], ["refresh-state"], ["extract-frames"], ["face-scan"], ["face-cluster", "--threshold", "0.80"], ["face-cluster-report"], ["apply-face-groups"], ["vision-scan"], ["__vision_index__"], ["apply-vision-labels"], ["dedupe-organized", "--apply"], ["__similarity_index__"], ["__transcribe__"], ["__metadata_index__"], ["__metadata_backfill__"], ["__semantic_index__"]],
    "workflow-transcribe-sample": [["__transcribe_sample__"], ["__metadata_index__"]],
    "model-pull-openclip-vit-l": [["__model_pull__", "openclip-vit-l"]],
    "model-pull-openclip-vit-h": [["__model_pull__", "openclip-vit-h"]],
    "model-pull-insightface-buffalo-l": [["__model_pull__", "insightface-buffalo-l"]],
    "model-pull-faster-whisper-small": [["__model_pull__", "faster-whisper-small"]],
    "model-pull-funasr-nano-onnx": [["__model_pull__", "funasr-nano-onnx"]],
    "model-pull-sensevoice-small-gguf": [["__model_pull__", "sensevoice-small-gguf"]],
    "model-pull-sensevoice-fsmn-vad-gguf": [["__model_pull__", "sensevoice-fsmn-vad-gguf"]],
    "model-pull-sensevoice-llamacpp-runtime": [["__model_pull__", "sensevoice-llamacpp-runtime"]],
    "model-pull-custom-detector-onnx": [["__model_pull__", "custom-detector-onnx"]],
    "model-pull-recommended": [["__model_pull__", "openclip-vit-l"], ["__model_pull__", "insightface-buffalo-l"], ["__model_pull__", "sensevoice-small-gguf"], ["__model_pull__", "sensevoice-fsmn-vad-gguf"], ["__model_pull__", "sensevoice-llamacpp-runtime"]],
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
    "extract-frames-retry-failed": ["extract-frames", "--retry-failed"],
    "face-setup": ["face-setup"],
    "face-scan-sample": ["face-scan", "--limit", "120"],
    "face-scan": ["face-scan"],
    "vision-scan-sample": ["vision-scan", "--limit", "120"],
    "vision-scan": ["vision-scan"],
    "vision-scan-strong": ["vision-scan"],
    "index-vision": ["__vision_index__"],
    "train-vision-calibrator": ["__vision_calibrator_train__"],
    "face-cluster": ["face-cluster", "--threshold", "0.75"],
    "face-cluster-balanced": ["face-cluster", "--threshold", "0.80"],
    "face-cluster-relaxed": ["face-cluster", "--threshold", "0.90"],
    "face-cluster-report": ["face-cluster-report"],
    "apply-face-groups-dry-run": ["apply-face-groups"],
    "apply-face-groups": ["apply-face-groups", "--apply"],
    "apply-vision-labels-dry-run": ["apply-vision-labels"],
    "apply-vision-labels": ["apply-vision-labels", "--apply"],
    "index-metadata": ["__metadata_index__"],
    "metadata-backfill": ["__metadata_backfill__"],
    "repair-thumbnails": ["__thumbnail_repair__"],
    "index-similarity": ["__similarity_index__"],
    "index-semantic": ["__semantic_index__"],
    "transcribe-sample": ["__transcribe_sample__"],
    "transcribe": ["__transcribe__"],
}


PIPELINE_STAGES = {
    "scan": "scan",
    "analyze-filenames": "filename-analysis",
    "classify-keywords": "keyword-classification",
    "apply": "apply-move-plan",
    "normalize-organized": "normalize",
    "organize-review": "review-cleanup",
    "refresh-state": "refresh-state",
    "extract-frames": "extract-frames",
    "face-scan": "face-scan",
    "face-cluster": "face-cluster",
    "face-cluster-report": "face-report",
    "apply-face-groups": "apply-face-groups",
    "vision-scan": "vision-scan",
    "apply-vision-labels": "apply-vision-labels",
    "dedupe-organized": "dedupe",
    "__vision_index__": "index-vision",
    "__vision_calibrator_train__": "train-vision-calibrator",
    "__metadata_index__": "index-metadata",
    "__metadata_backfill__": "metadata-backfill",
    "__thumbnail_repair__": "thumbnail-repair",
    "__similarity_index__": "index-similarity",
    "__semantic_index__": "index-semantic",
    "__transcribe_sample__": "transcribe",
    "__transcribe__": "transcribe",
    "__model_pull__": "model-download",
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
        cur = conn.execute("INSERT INTO jobs (command, status, message, progress) VALUES (?, 'queued', '', 0)", (command,))
        job_id = int(cur.lastrowid)
    thread = threading.Thread(target=run_job, args=(job_id, command), daemon=True)
    thread.start()
    return job_id


def mark_interrupted_jobs() -> int:
    with connect() as conn:
        rows = conn.execute("SELECT id FROM jobs WHERE status IN ('queued', 'running')").fetchall()
        if not rows:
            return 0
        conn.execute(
            """
            UPDATE jobs
            SET status='failed',
                progress=0,
                finished_at=CURRENT_TIMESTAMP,
                message='interrupted by service restart; cached outputs are kept and the job can be rerun',
                stderr=CASE
                    WHEN stderr='' THEN 'interrupted by service restart'
                    ELSE stderr || char(10) || 'interrupted by service restart'
                END,
                heartbeat_at=CURRENT_TIMESTAMP
            WHERE status IN ('queued', 'running')
            """
        )
    return len(rows)


def cancel_file(job_id: int) -> Path:
    return Path(os.environ.get("JOB_CANCEL_DIR", "/tmp/tgmm-jobs")) / f"{job_id}.cancel"


def request_job_cancel(job_id: int) -> None:
    with connect() as conn:
        row = conn.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise ValueError("Job not found")
        conn.execute("UPDATE jobs SET cancel_requested=1, message='cancel requested', heartbeat_at=CURRENT_TIMESTAMP WHERE id=?", (job_id,))
    path = cancel_file(job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("cancel requested\n", encoding="utf-8")


def is_cancel_requested(job_id: int) -> bool:
    if cancel_file(job_id).exists():
        return True
    with connect() as conn:
        row = conn.execute("SELECT cancel_requested FROM jobs WHERE id=?", (job_id,)).fetchone()
    return bool(row and row["cancel_requested"])


def hardware_env(settings: dict) -> dict[str, str]:
    env = os.environ.copy()
    compute = (settings.get("compute_device") or os.environ.get("COMPUTE_DEVICE", "auto")).lower()
    ffmpeg = settings.get("ffmpeg_hwaccel") or os.environ.get("FFMPEG_HWACCEL", "auto")
    face = settings.get("face_providers") or os.environ.get("FACE_PROVIDERS", "")
    openvino = settings.get("openvino_device") or os.environ.get("OPENVINO_DEVICE", "")
    whisper = settings.get("whisper_device") or os.environ.get("WHISPER_DEVICE", "cpu")
    asr_engine = settings.get("asr_engine") or os.environ.get("ASR_ENGINE", "auto")
    transcript_engine = settings.get("transcript_engine") or os.environ.get("TRANSCRIPT_ENGINE", asr_engine)
    audio_tag_mode = settings.get("audio_tag_mode") or os.environ.get("AUDIO_TAG_MODE", "sensevoice-sample")
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
    env["FFMPEG_HW_DEVICE"] = settings.get("ffmpeg_hw_device") or os.environ.get("FFMPEG_HW_DEVICE", "/dev/dri/renderD128")
    env["FACE_PROVIDERS"] = face or "OpenVINOExecutionProvider,CPUExecutionProvider"
    env["OPENVINO_DEVICE"] = openvino or "GPU"
    env["OPENCLIP_MODEL"] = settings.get("openclip_model") or os.environ.get("OPENCLIP_MODEL", "ViT-L-14")
    env["OPENCLIP_PRETRAINED"] = settings.get("openclip_pretrained") or os.environ.get("OPENCLIP_PRETRAINED", "laion2b_s32b_b82k")
    env["OPENCLIP_STRONG_MODEL"] = settings.get("openclip_strong_model") or os.environ.get("OPENCLIP_STRONG_MODEL", "ViT-H-14")
    env["OPENCLIP_STRONG_PRETRAINED"] = settings.get("openclip_strong_pretrained") or os.environ.get("OPENCLIP_STRONG_PRETRAINED", "laion2b_s32b_b79k")
    env["OPENCLIP_STRONG_THRESHOLD"] = str(settings.get("openclip_strong_threshold") or os.environ.get("OPENCLIP_STRONG_THRESHOLD", "0.62"))
    env["OPENCLIP_STRONG_LOW_CONF_ONLY"] = str(settings.get("openclip_strong_low_conf_only") or os.environ.get("OPENCLIP_STRONG_LOW_CONF_ONLY", "true"))
    env["WHISPER_DEVICE"] = whisper
    env.setdefault("WHISPER_COMPUTE_TYPE", "int8")
    env["ASR_ENGINE"] = asr_engine
    env["TRANSCRIPT_ENGINE"] = transcript_engine
    env["AUDIO_TAG_MODE"] = audio_tag_mode
    env["AUDIO_TAG_SAMPLE_SECONDS"] = str(settings.get("audio_tag_sample_seconds") or os.environ.get("AUDIO_TAG_SAMPLE_SECONDS", "30"))
    env["SENSEVOICE_GGUF_BIN"] = settings.get("sensevoice_gguf_bin") or os.environ.get("SENSEVOICE_GGUF_BIN", "llama-sensevoice")
    env["SENSEVOICE_GGUF_MODEL"] = settings.get("sensevoice_gguf_model") or os.environ.get("SENSEVOICE_GGUF_MODEL", "/models/sensevoice/SenseVoiceSmall.gguf")
    if settings.get("sensevoice_gguf_command") or os.environ.get("SENSEVOICE_GGUF_COMMAND"):
        env["SENSEVOICE_GGUF_COMMAND"] = settings.get("sensevoice_gguf_command") or os.environ.get("SENSEVOICE_GGUF_COMMAND", "")
    env["FRAME_WORKERS"] = str(settings.get("frame_workers") or os.environ.get("FRAME_WORKERS", "1"))
    env["FRAME_CHECKPOINT_EVERY"] = str(settings.get("frame_checkpoint_every") or os.environ.get("FRAME_CHECKPOINT_EVERY", "100"))
    env["TRANSCRIBE_MAX_SECONDS"] = str(settings.get("transcribe_max_seconds") or os.environ.get("TRANSCRIBE_MAX_SECONDS", "0"))
    return env


def update_job_progress(job_id: int, **values) -> None:
    allowed = {
        "stage", "current_item", "processed", "total", "success_count", "failed_count",
        "skipped_count", "progress", "message", "stdout", "stderr",
    }
    fields = []
    params = []
    for key, value in values.items():
        if key in allowed:
            fields.append(f"{key}=?")
            params.append(value)
    fields.append("heartbeat_at=CURRENT_TIMESTAMP")
    params.append(job_id)
    with connect() as conn:
        conn.execute(f"UPDATE jobs SET {', '.join(fields)} WHERE id=?", params)


def step_stage(step: list[str]) -> str:
    return PIPELINE_STAGES.get(step[0], step[0] if step else "job")


def apply_dynamic_step_args(step: list[str], settings: dict) -> list[str]:
    if not step:
        return step
    out = list(step)
    if step[0] == "extract-frames":
        if "--workers" not in out:
            out.extend(["--workers", str(settings.get("frame_workers") or os.environ.get("FRAME_WORKERS", "1"))])
        if "--checkpoint-every" not in out:
            out.extend(["--checkpoint-every", str(settings.get("frame_checkpoint_every") or os.environ.get("FRAME_CHECKPOINT_EVERY", "100"))])
        frames = str(settings.get("frames_per_video") or os.environ.get("FRAMES_PER_VIDEO", "3"))
        if "--frames" not in out:
            out.extend(["--frames", frames])
    return out


def record_progress_line(job_id: int, line: str, stage: str, stdout_tail: list[str]) -> None:
    if not line.startswith("TGMM_PROGRESS "):
        return
    try:
        payload = json.loads(line.removeprefix("TGMM_PROGRESS ").strip())
    except json.JSONDecodeError:
        return
    processed = int(payload.get("processed") or 0)
    total = int(payload.get("total") or 0)
    progress = int(payload.get("progress") or (processed / total * 100 if total else 0))
    update_job_progress(
        job_id,
        stage=str(payload.get("stage") or stage),
        processed=processed,
        total=total,
        progress=max(0, min(99, progress)),
        current_item=str(payload.get("current") or payload.get("current_item") or ""),
        failed_count=int(payload.get("failed") or payload.get("failed_count") or 0),
        skipped_count=int(payload.get("cached_or_done") or payload.get("skipped") or 0),
        message=str(payload.get("message") or f"{stage}: {processed}/{total}"),
        stdout="\n".join(stdout_tail)[-20000:],
    )


def run_external_step(job_id: int, step_args: list[str], env: dict, stage: str) -> tuple[int, str, str]:
    stdout_lines: list[str] = []
    stderr_text = ""
    proc = subprocess.Popen(
        step_args,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**env, "TGMM_CANCEL_FILE": str(cancel_file(job_id))},
        start_new_session=True,
    )
    last_heartbeat = time.time()
    while True:
        if proc.stdout is not None:
            ready, _, _ = select.select([proc.stdout], [], [], 0.2)
            if ready:
                line = proc.stdout.readline()
                if line:
                    line = line.rstrip("\n")
                    stdout_lines.append(line)
                    stdout_lines = stdout_lines[-400:]
                    record_progress_line(job_id, line, stage, stdout_lines)
        if proc.poll() is not None:
            if proc.stdout is not None:
                for line in proc.stdout:
                    line = line.rstrip("\n")
                    stdout_lines.append(line)
                    stdout_lines = stdout_lines[-400:]
                    record_progress_line(job_id, line, stage, stdout_lines)
            break
        if is_cancel_requested(job_id):
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except Exception:
                proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except Exception:
                    proc.kill()
            return 130, "\n".join(stdout_lines), "cancelled"
        if time.time() - last_heartbeat > 5:
            update_job_progress(job_id, stage=stage, message=f"{stage} running", stdout="\n".join(stdout_lines)[-20000:])
            last_heartbeat = time.time()
        time.sleep(0.05)
    if proc.stderr is not None:
        stderr_text = proc.stderr.read()
    return proc.wait(), "\n".join(stdout_lines), stderr_text


class ProgressCapture:
    def __init__(self, job_id: int, stage: str):
        self.job_id = job_id
        self.stage = stage
        self.lines: list[str] = []
        self._buffer = ""

    def write(self, text: str) -> int:
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line:
                self.lines.append(line)
                self.lines = self.lines[-400:]
                record_progress_line(self.job_id, line, self.stage, self.lines)
        return len(text)

    def flush(self) -> None:
        if self._buffer:
            line = self._buffer
            self._buffer = ""
            self.lines.append(line)
            self.lines = self.lines[-400:]
            record_progress_line(self.job_id, line, self.stage, self.lines)

    def text(self) -> str:
        self.flush()
        return "\n".join(self.lines)

    def snapshot(self) -> str:
        lines = list(self.lines)
        if self._buffer:
            lines.append(self._buffer)
        return "\n".join(lines)


def run_internal_with_progress(job_id: int, stage: str, fn, heartbeat_message: str | None = None):
    capture = ProgressCapture(job_id, stage)
    state: dict[str, object] = {}

    def target() -> None:
        try:
            with redirect_stdout(capture):
                state["result"] = fn()
        except BaseException as exc:
            state["error"] = exc

    thread = threading.Thread(target=target, daemon=True)
    started = time.time()
    thread.start()
    while thread.is_alive():
        elapsed = int(time.time() - started)
        message = heartbeat_message or f"{stage} running ({elapsed}s)"
        if is_cancel_requested(job_id):
            message = f"{stage} cancel requested; waiting for current step"
        update_job_progress(
            job_id,
            stage=stage,
            message=message,
            stdout=capture.snapshot()[-20000:],
        )
        thread.join(timeout=5)
    if state.get("error"):
        raise state["error"]  # type: ignore[misc]
    result = state.get("result")
    return result, capture.text()


def metadata_progress_printer(stage: str, processed: int, total: int, current: str) -> None:
    progress = int(processed / total * 100) if total else 0
    print(
        "TGMM_PROGRESS "
        + json.dumps(
            {
                "stage": stage,
                "processed": processed,
                "total": total,
                "progress": max(0, min(99, progress)),
                "current": current,
                "message": f"{stage}: {processed}/{total}" if total else stage,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


def run_job(job_id: int, command: str) -> None:
    settings = get_settings()
    media_root = settings.get("media_root") or os.environ.get("MEDIA_ROOT", "/media")
    output_root = settings.get("output_root") or os.environ.get("MEDIA_OUTPUT_ROOT") or media_root
    source_dirs = settings.get("source_dirs") or os.environ.get("MEDIA_SOURCE_DIRS", "")
    steps = ALLOWED_COMMANDS[command]
    if steps and isinstance(steps[0], str):
        steps = [steps]
    base_args = [sys.executable, str(core_script()), "--root", media_root, "--output-root", output_root]
    env = hardware_env(settings)
    cancel = cancel_file(job_id)
    try:
        cancel.unlink()
    except OSError:
        pass
    os.environ["TGMM_CANCEL_FILE"] = str(cancel)
    os.environ.update({
        key: value for key, value in env.items()
        if key in {
            "COMPUTE_DEVICE", "FFMPEG_HWACCEL", "FACE_PROVIDERS", "OPENVINO_DEVICE",
            "OPENCLIP_MODEL", "OPENCLIP_PRETRAINED", "OPENCLIP_STRONG_MODEL",
            "OPENCLIP_STRONG_PRETRAINED", "OPENCLIP_STRONG_THRESHOLD", "OPENCLIP_STRONG_LOW_CONF_ONLY",
            "WHISPER_DEVICE", "WHISPER_COMPUTE_TYPE", "ASR_ENGINE", "TRANSCRIPT_ENGINE", "AUDIO_TAG_MODE", "AUDIO_TAG_SAMPLE_SECONDS", "SENSEVOICE_GGUF_BIN",
            "SENSEVOICE_GGUF_MODEL", "SENSEVOICE_GGUF_COMMAND", "TRANSCRIBE_MAX_SECONDS",
        }
    })
    if source_dirs:
        base_args.extend(["--source-dirs", source_dirs])
    with connect() as conn:
        message = " && ".join(
            "index-metadata" if step == ["__metadata_index__"] else
            "metadata-backfill" if step == ["__metadata_backfill__"] else
            "repair-thumbnails" if step == ["__thumbnail_repair__"] else
            "index-vision" if step == ["__vision_index__"] else
            "train-vision-calibrator" if step == ["__vision_calibrator_train__"] else
            "index-similarity" if step == ["__similarity_index__"] else
            "transcribe-sample" if step == ["__transcribe_sample__"] else
            "transcribe" if step == ["__transcribe__"] else
            f"model-pull {step[1]}" if step and step[0] == "__model_pull__" else
            " ".join([*base_args, *step])
            for step in steps
        )
        conn.execute("UPDATE jobs SET status='running', started_at=CURRENT_TIMESTAMP, message=? WHERE id=?", (message, job_id))
    try:
        stdout_parts = []
        stderr_parts = []
        returncode = 0
        total_steps = len(steps)
        for index, step in enumerate(steps, start=1):
            if is_cancel_requested(job_id):
                returncode = 130
                break
            stage = step_stage(step)
            update_job_progress(job_id, stage=stage, progress=int((index - 1) / max(1, total_steps) * 100), message=f"{stage} ({index}/{total_steps})")
            if step == ["__metadata_index__"]:
                result, captured = run_internal_with_progress(
                    job_id,
                    "index-metadata",
                    lambda: rebuild_metadata_index(Path(output_root), progress=metadata_progress_printer, cancel_check=lambda: is_cancel_requested(job_id)),
                    "index-metadata running",
                )
                stdout_parts.append(f"$ index-metadata\n{captured}\n{result}")
                returncode = 130 if result.get("cancelled") else 0
            elif step == ["__metadata_backfill__"]:
                result, captured = run_internal_with_progress(
                    job_id,
                    "metadata-backfill",
                    lambda: backfill_media_metadata(Path(output_root), progress=metadata_progress_printer, cancel_check=lambda: is_cancel_requested(job_id)),
                    "metadata backfill running",
                )
                stdout_parts.append(f"$ metadata-backfill\n{captured}\n{result}")
                returncode = 130 if result.get("cancelled") else (0 if result.get("ok") else 1)
            elif step == ["__thumbnail_repair__"]:
                result, captured = run_internal_with_progress(
                    job_id,
                    "thumbnail-repair",
                    lambda: repair_thumbnail_cache(Path(output_root), progress=metadata_progress_printer, cancel_check=lambda: is_cancel_requested(job_id)),
                    "thumbnail repair running",
                )
                stdout_parts.append(f"$ repair-thumbnails\n{captured}\n{result}")
                returncode = 130 if result.get("cancelled") else (0 if result.get("ok") else 1)
            elif step == ["__vision_index__"]:
                result = import_vision_outputs(Path(output_root))
                stdout_parts.append(f"$ index-vision\n{result}")
            elif step == ["__vision_calibrator_train__"]:
                result = train_vision_calibrators(Path(output_root))
                stdout_parts.append(f"$ train-vision-calibrator\n{result}")
                returncode = 0
            elif step == ["__similarity_index__"]:
                result = rebuild_similarity_index(Path(output_root))
                stdout_parts.append(f"$ index-similarity\n{result}")
                returncode = 0
            elif step == ["__semantic_index__"]:
                result, captured = run_internal_with_progress(
                    job_id,
                    "index-semantic",
                    lambda: rebuild_semantic_index(Path(output_root), progress=metadata_progress_printer, cancel_check=lambda: is_cancel_requested(job_id)),
                    "semantic index running",
                )
                stdout_parts.append(f"$ index-semantic\n{captured}\n{result}")
                returncode = 130 if result.get("cancelled") else (0 if result.get("ok") else 1)
            elif step == ["__transcribe_sample__"]:
                update_job_progress(job_id, stage="transcribe", message="transcribe sample running")
                result, captured = run_internal_with_progress(job_id, "transcribe", lambda: transcribe_videos(Path(output_root), limit=5), "transcribe sample still running")
                stdout_parts.append(f"$ transcribe-sample\n{captured}\n{result}")
                returncode = 130 if result.get("cancelled") else (0 if result.get("ok") else 1)
            elif step == ["__transcribe__"]:
                update_job_progress(job_id, stage="transcribe", message="full transcribe running")
                result, captured = run_internal_with_progress(job_id, "transcribe", lambda: transcribe_videos(Path(output_root), limit=None), "full transcribe still running")
                stdout_parts.append(f"$ transcribe\n{captured}\n{result}")
                returncode = 130 if result.get("cancelled") else (0 if result.get("ok") else 1)
            elif step and step[0] == "__model_pull__":
                model_id = step[1]
                update_job_progress(job_id, stage="model-download", message=f"pulling {model_id}")
                os.environ["TGMM_CANCEL_FILE"] = str(cancel_file(job_id))
                result, captured = run_internal_with_progress(job_id, "model-download", lambda: pull_model(model_id), f"pulling {model_id}; third-party download may report only when finished")
                stdout_parts.append(f"$ model-pull {model_id}\n{captured}\n{result}")
                returncode = 130 if result.get("cancelled") else (0 if result.get("ok") else 1)
            else:
                dynamic_step = apply_dynamic_step_args(step, settings)
                step_args = [*base_args, *dynamic_step]
                step_env = dict(env)
                if command == "vision-scan-strong" and dynamic_step and dynamic_step[0] == "vision-scan":
                    step_env["OPENCLIP_STRONG_MODE"] = "true"
                code, out, err = run_external_step(job_id, step_args, step_env, stage)
                stdout_parts.append(f"$ {' '.join(step_args)}\n{out}")
                if err:
                    stderr_parts.append(f"$ {' '.join(step_args)}\n{err}")
                returncode = code
                if code != 0:
                    break
            update_job_progress(job_id, progress=int(index / max(1, total_steps) * 100), message=f"{stage} done")
        status = "done" if returncode == 0 else ("cancelled" if returncode == 130 else "failed")
        with connect() as conn:
            if status == "done":
                conn.execute(
                    "UPDATE jobs SET status=?, progress=100, finished_at=CURRENT_TIMESTAMP, stdout=?, stderr=?, message=?, heartbeat_at=CURRENT_TIMESTAMP WHERE id=?",
                    (status, "\n".join(stdout_parts)[-20000:], "\n".join(stderr_parts)[-20000:], f"exit {returncode}", job_id),
                )
            else:
                conn.execute(
                    "UPDATE jobs SET status=?, finished_at=CURRENT_TIMESTAMP, stdout=?, stderr=?, message=?, heartbeat_at=CURRENT_TIMESTAMP WHERE id=?",
                    (status, "\n".join(stdout_parts)[-20000:], "\n".join(stderr_parts)[-20000:], f"exit {returncode}", job_id),
                )
    except Exception as exc:
        with connect() as conn:
            conn.execute(
                "UPDATE jobs SET status='failed', finished_at=CURRENT_TIMESTAMP, stderr=?, message=? WHERE id=?",
                (repr(exc), "exception", job_id),
            )

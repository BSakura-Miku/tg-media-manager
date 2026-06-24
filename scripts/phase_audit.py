#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    full = REPO_ROOT / path
    if not full.exists():
        return ""
    return full.read_text(encoding="utf-8", errors="replace")


def file_exists(path: str) -> bool:
    return (REPO_ROOT / path).exists()


def has_all(path: str, needles: list[str]) -> bool:
    text = read_text(path)
    return all(needle in text for needle in needles)


PHASES = [
    {
        "id": "phase_1",
        "name": "Product UX and workflow foundation",
        "checks": [
            ("App shell and navigation", lambda: has_all("frontend/src/main.jsx", ["const nav =", "dashboard", "jobs", "library", "tagGraph", "randomFlow", "models", "authors", "faces"])),
            ("Guided workflow commands", lambda: has_all("backend/app/jobs.py", ["workflow-full-library", "workflow-new-downloads", "workflow-review-cleanup", "workflow-face-balanced", "workflow-vision-plan"])),
            ("Workflow step progress", lambda: has_all("frontend/src/main.jsx", ["workflowSteps", "jobWorkflowInfo", "remaining"])),
            ("Media viewer actions", lambda: has_all("frontend/src/main.jsx", ["toggleFavorite", "deleteMedia", "saveManualTag", "saveAuthor"])),
        ],
    },
    {
        "id": "phase_2",
        "name": "Metadata database and virtual classification",
        "checks": [
            ("SQLite media schema", lambda: has_all("backend/app/db.py", ["CREATE TABLE IF NOT EXISTS media_items", "CREATE TABLE IF NOT EXISTS media_tags", "CREATE TABLE IF NOT EXISTS media_operations"])),
            ("Parser and virtual fields", lambda: has_all("backend/app/db.py", ["parser_templates", "original_name", "normalized_path", "risk_state"])),
            ("Metadata indexer", lambda: has_all("backend/app/metadata.py", ["def rebuild_metadata_index", "original_name", "filename"])),
            ("Virtual search endpoints", lambda: has_all("backend/app/main.py", ['@app.get("/api/media")', "/api/media/{media_id}", "media_detail"])),
        ],
    },
    {
        "id": "phase_3",
        "name": "Vision tags and video understanding",
        "checks": [
            ("Frame extraction command", lambda: has_all("backend/core/tg_media_library.py", ["extract-frames", "frame_index.csv"])),
            ("OpenCLIP vision labels", lambda: has_all("backend/core/tg_media_library.py", ["open_clip", "vision-scan", "vision_labels.csv"])),
            ("Timeline import", lambda: has_all("backend/app/metadata.py", ["media_timeline_segments", "representative_frame", "import_vision_outputs"])),
            ("Manual feedback calibrator", lambda: has_all("backend/app/metadata.py", ["tag_feedback", "train_vision_calibrators", "vision_calibrators"])),
        ],
    },
    {
        "id": "phase_4",
        "name": "Deduplication, similarity, and versions",
        "checks": [
            ("Exact dedupe workflow", lambda: has_all("backend/app/jobs.py", ["dedupe-organized", "dedupe-organized-dry-run"])),
            ("Similarity tables", lambda: has_all("backend/app/db.py", ["similarity_groups", "similarity_members"])),
            ("Similarity indexer", lambda: has_all("backend/app/metadata.py", ["def rebuild_similarity_index", "upsert_similarity_group"])),
            ("Similarity UI", lambda: has_all("frontend/src/main.jsx", ["SimilarityPanel", "SimilarityCard", "rebuildSimilarity"])),
        ],
    },
    {
        "id": "phase_5",
        "name": "Privacy, compliance, models, and performance",
        "checks": [
            ("Model manager", lambda: has_all("backend/app/model_manager.py", ["MODEL_REGISTRY", "model_catalog", "pull_model", "MODEL_ROOT"])),
            ("Authentication support", lambda: has_all("backend/app/main.py", ["/api/auth/status", "APP_PASSWORD"])),
            ("Subtitle/transcript support", lambda: has_all("backend/app/metadata.py", ["write_subtitle_files", "subtitle_for_media", "transcribe_videos"])),
            ("GPU/runtime settings", lambda: has_all("frontend/src/main.jsx", ["ffmpegHwaccel", "openvinoDevice", "faceProviders", "transcriptEngine"])),
            ("Model architecture record", lambda: file_exists("docs/architecture-model-management.md")),
        ],
    },
]


def audit_code() -> list[dict]:
    results = []
    for phase in PHASES:
        checks = []
        for label, fn in phase["checks"]:
            ok = False
            error = ""
            try:
                ok = bool(fn())
            except Exception as exc:  # pragma: no cover - defensive report path
                error = str(exc)
            checks.append({"name": label, "ok": ok, "error": error})
        results.append(
            {
                "id": phase["id"],
                "name": phase["name"],
                "ok": all(item["ok"] for item in checks),
                "checks": checks,
            }
        )
    return results


def db_counts(db_path: Path) -> dict:
    if not db_path.exists():
        return {"exists": False, "path": str(db_path)}
    wanted = [
        "jobs",
        "media_items",
        "media_tags",
        "media_operations",
        "media_timeline_segments",
        "similarity_groups",
        "similarity_members",
        "media_transcripts",
        "tag_feedback",
        "vision_calibrators",
    ]
    out = {"exists": True, "path": str(db_path), "tables": {}}
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        existing = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in wanted:
            if table not in existing:
                out["tables"][table] = None
                continue
            out["tables"][table] = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        running = conn.execute("SELECT id, command, status, progress, stage, processed, total FROM jobs WHERE status IN ('queued','running') ORDER BY id DESC LIMIT 5").fetchall() if "jobs" in existing else []
        out["running_jobs"] = [dict(row) for row in running]
    return out


def media_root_counts(root: Path) -> dict:
    if not root.exists():
        return {"exists": False, "path": str(root)}
    manifests = root / "_MANIFESTS"
    outputs = {
        "manifest_all.csv": manifests / "manifest_all.csv",
        "move_plan.csv": manifests / "move_plan.csv",
        "applied_moves.csv": manifests / "applied_moves.csv",
        "frame_index.csv": manifests / "frame_index.csv",
        "face_index.csv": manifests / "face_index.csv",
        "face_groups.csv": manifests / "face_groups.csv",
        "vision_labels.csv": manifests / "vision_labels.csv",
    }
    result = {"exists": True, "path": str(root), "outputs": {}, "subtitle_files": 0}
    for name, path in outputs.items():
        result["outputs"][name] = {"exists": path.exists(), "bytes": path.stat().st_size if path.exists() else 0}
    subtitles = manifests / "subtitles"
    if subtitles.exists():
        result["subtitle_files"] = sum(1 for item in subtitles.rglob("*.vtt") if item.is_file())
    return result


def warnings(report: dict) -> list[str]:
    found = []
    for phase in report["code_phases"]:
        if not phase["ok"]:
            failed = ", ".join(item["name"] for item in phase["checks"] if not item["ok"])
            found.append(f"{phase['id']} code checks failed: {failed}")
    db = report.get("database") or {}
    if db.get("exists"):
        tables = db.get("tables", {})
        for table in ["media_items", "media_tags", "media_operations"]:
            if not tables.get(table):
                found.append(f"database table {table} is empty")
    media = report.get("media_root") or {}
    if media.get("exists"):
        outputs = media.get("outputs", {})
        for name in ["manifest_all.csv", "frame_index.csv", "vision_labels.csv"]:
            item = outputs.get(name) or {}
            if not item.get("exists"):
                found.append(f"missing media output {name}")
    return found


def print_markdown(report: dict) -> None:
    print("# TGMM Phase Audit")
    print()
    print("## Code Phases")
    for phase in report["code_phases"]:
        print(f"- [{'x' if phase['ok'] else ' '}] {phase['id']}: {phase['name']}")
        for check in phase["checks"]:
            suffix = f" ({check['error']})" if check["error"] else ""
            print(f"  - [{'x' if check['ok'] else ' '}] {check['name']}{suffix}")
    if report.get("database"):
        db = report["database"]
        print()
        print("## Database")
        print(f"- Path: `{db.get('path')}`")
        print(f"- Exists: {db.get('exists')}")
        for table, count in (db.get("tables") or {}).items():
            print(f"- {table}: {count if count is not None else 'missing'}")
        if db.get("running_jobs"):
            print("- Running jobs:")
            for job in db["running_jobs"]:
                print(f"  - #{job.get('id')} {job.get('command')} {job.get('status')} {job.get('progress')}% {job.get('stage')} {job.get('processed')}/{job.get('total')}")
    if report.get("media_root"):
        media = report["media_root"]
        print()
        print("## Media Root")
        print(f"- Path: `{media.get('path')}`")
        print(f"- Exists: {media.get('exists')}")
        for name, item in (media.get("outputs") or {}).items():
            print(f"- {name}: {'yes' if item.get('exists') else 'no'} ({item.get('bytes', 0)} bytes)")
        print(f"- subtitle_files: {media.get('subtitle_files', 0)}")
    print()
    print("## Warnings")
    if report["warnings"]:
        for item in report["warnings"]:
            print(f"- {item}")
    else:
        print("- none")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit TG Media Manager phase readiness.")
    parser.add_argument("--db", type=Path, help="Path to tg_media_manager.sqlite3")
    parser.add_argument("--media-root", type=Path, help="Path to mounted media root")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown")
    args = parser.parse_args()

    report = {"code_phases": audit_code()}
    if args.db:
        report["database"] = db_counts(args.db)
    if args.media_root:
        report["media_root"] = media_root_counts(args.media_root)
    report["warnings"] = warnings(report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_markdown(report)
    return 0 if not any(not phase["ok"] for phase in report["code_phases"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())

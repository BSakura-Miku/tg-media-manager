from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from backend.app import db, jobs
from backend.app.jobs import ALLOWED_COMMANDS, assess_quality_gate
from backend.core import tg_media_library


class WorkflowQualityTests(unittest.TestCase):
    def test_full_workflow_repairs_thumbnails_and_runs_quality_gate(self) -> None:
        steps = ALLOWED_COMMANDS["workflow-full-library"]
        self.assertIn(["__thumbnail_repair__"], steps)
        self.assertEqual(steps[-1], ["__quality_gate__"])

    def test_hash_backfill_can_be_resumed_independently(self) -> None:
        self.assertEqual(ALLOWED_COMMANDS["hash-backfill"], ["__hash_backfill__"])

    def test_quality_gate_reports_missing_capabilities(self) -> None:
        result = assess_quality_gate(
            {
                "media": {"face_group_rows": 20, "faces": 0},
                "coverage": [
                    {"id": "dimensions", "total": 100, "percent": 99},
                    {"id": "duration", "total": 50, "percent": 98},
                    {"id": "resolution", "total": 100, "percent": 99},
                    {"id": "tags", "total": 100, "percent": 95},
                    {"id": "thumbnails", "total": 100, "percent": 4},
                    {"id": "text_vectors", "total": 100, "percent": 100},
                    {"id": "image_vectors", "total": 100, "percent": 100},
                    {"id": "timed_subtitles", "total": 50, "percent": 1},
                ],
            }
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("thumbnails" in warning for warning in result["warnings"]))
        self.assertTrue(any("timed subtitle" in warning for warning in result["warnings"]))
        self.assertTrue(any("face groups" in warning for warning in result["warnings"]))

    def test_quality_gate_accepts_complete_index(self) -> None:
        result = assess_quality_gate(
            {
                "media": {"face_group_rows": 20, "faces": 18},
                "coverage": [
                    {"id": capability, "total": 100, "percent": 100}
                    for capability in (
                        "dimensions",
                        "duration",
                        "resolution",
                        "tags",
                        "thumbnails",
                        "text_vectors",
                        "image_vectors",
                        "timed_subtitles",
                    )
                ],
            }
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["warnings"], [])

    def test_completed_job_cannot_be_cancelled(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir, patch.dict(
            jobs.os.environ,
            {"APP_DB": str(Path(tempdir) / "jobs.sqlite3"), "JOB_CANCEL_DIR": str(Path(tempdir) / "cancel")},
            clear=False,
        ):
            db.init_db()
            with db.connect() as conn:
                job_id = int(conn.execute("INSERT INTO jobs(command,status) VALUES ('scan','done')").lastrowid)
            with self.assertRaisesRegex(RuntimeError, "already done"):
                jobs.request_job_cancel(job_id)

    def test_frame_checkpoint_merges_existing_index(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "_MANIFESTS").mkdir()
            (root / "a.jpg").write_bytes(b"a")
            (root / "b.jpg").write_bytes(b"b")
            config = tg_media_library.Config(root=root)
            tg_media_library.write_frame_index(config, [{
                "media_path": "a.jpg", "cache_key": "a", "kind": "photo", "frames": "a-frame.jpg",
                "frame_times": "", "contact_sheet": "", "error": "",
            }])
            tg_media_library.write_frame_index(config, [{
                "media_path": "b.jpg", "cache_key": "b", "kind": "photo", "frames": "b-frame.jpg",
                "frame_times": "", "contact_sheet": "", "error": "",
            }])
            rows = list(tg_media_library.dict_rows_from_csv(config.manifests / "frame_index.csv"))
            self.assertEqual({row["media_path"] for row in rows}, {"a.jpg", "b.jpg"})


if __name__ == "__main__":
    unittest.main()

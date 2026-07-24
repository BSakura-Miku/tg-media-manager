from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

from backend.app import db, jobs, main


class JobApiQueueingTests(unittest.TestCase):
    def test_job_status_filter_supports_warning_and_interrupted(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir, patch.dict(
            main.os.environ,
            {"APP_DB": str(Path(tempdir) / "jobs.sqlite3")},
            clear=False,
        ):
            db.init_db()
            with db.connect() as conn:
                conn.executemany(
                    "INSERT INTO jobs(command, status) VALUES (?, ?)",
                    [
                        ("scan", "done"),
                        ("transcribe", "warning"),
                        ("index-metadata", "interrupted"),
                    ],
                )

            warnings = main.api_jobs(limit=20, status="warning")
            interrupted = main.api_jobs(limit=20, status="interrupted")

        self.assertEqual([row["status"] for row in warnings], ["warning"])
        self.assertEqual([row["status"] for row in interrupted], ["interrupted"])

    def test_heavy_endpoints_only_enqueue_jobs(self) -> None:
        with patch.object(main, "create_job", side_effect=[41, 42]) as create_job:
            metadata = main.api_metadata_backfill(limit=37)
            calibrator = main.api_train_vision_calibrator()

        self.assertEqual(
            create_job.call_args_list,
            [
                call("metadata-backfill", options={"limit": 37}),
                call("train-vision-calibrator"),
            ],
        )
        self.assertEqual(metadata["id"], 41)
        self.assertTrue(metadata["queued"])
        self.assertEqual(calibrator["id"], 42)
        self.assertTrue(calibrator["queued"])

    def test_metadata_backfill_job_forwards_validated_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir, patch.dict(
            jobs.os.environ,
            {
                "APP_DB": str(Path(tempdir) / "jobs.sqlite3"),
                "JOB_CANCEL_DIR": str(Path(tempdir) / "cancel"),
                "MEDIA_ROOT": tempdir,
                "MEDIA_OUTPUT_ROOT": tempdir,
            },
            clear=False,
        ):
            db.init_db()
            with db.connect() as conn:
                job_id = int(
                    conn.execute(
                        "INSERT INTO jobs(command, status) VALUES ('metadata-backfill', 'queued')"
                    ).lastrowid
                )
            with patch.object(
                jobs,
                "backfill_media_metadata",
                return_value={
                    "ok": True,
                    "cancelled": False,
                    "processed": 0,
                    "failed": 0,
                },
            ) as backfill:
                jobs.run_job(job_id, "metadata-backfill", {"limit": 37})
            with db.connect() as conn:
                status = conn.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()["status"]

        self.assertEqual(backfill.call_args.kwargs["limit"], 37)
        self.assertEqual(status, "done")

    def test_job_options_reject_unsupported_or_out_of_range_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported options"):
            jobs.normalize_job_options("transcribe", {"limit": 5})
        with self.assertRaisesRegex(ValueError, "between 1 and 5000"):
            jobs.normalize_job_options("metadata-backfill", {"limit": 0})


if __name__ == "__main__":
    unittest.main()

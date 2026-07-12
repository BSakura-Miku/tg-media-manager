from __future__ import annotations

import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import Response

from backend.app import db, main, model_manager


class AuthSessionTests(unittest.TestCase):
    def test_signed_session_expires_and_rejects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir, patch.dict(main.os.environ, {
            "APP_DB": str(Path(tempdir) / "auth.sqlite3"),
            "APP_PASSWORD": "test-password",
            "APP_SECRET": "test-signing-secret",
            "APP_SESSION_TTL_SECONDS": "600",
        }, clear=False):
            db.init_db()
            token = main.issue_auth_token(now=1_000)
            self.assertTrue(main.auth_session_valid(token, now=1_300))
            self.assertFalse(main.auth_session_valid(token, now=1_601))
            self.assertFalse(main.auth_session_valid(token + "changed", now=1_300))
            self.assertFalse(main.auth_session_valid("\u2603.invalid", now=1_300))

    def test_disabled_auth_reports_exposure_risk(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir, patch.dict(
            main.os.environ,
            {"APP_DB": str(Path(tempdir) / "auth.sqlite3"), "APP_PASSWORD": "", "APP_LOCAL_ONLY": "false"},
            clear=False,
        ):
            db.init_db()
            status = main.auth_security_status()
        self.assertFalse(status["enabled"])
        self.assertFalse(status["local_only"])
        self.assertTrue(status["exposed_without_auth"])
        self.assertTrue(status["security_warnings"])

    def test_password_change_persists_and_invalidates_previous_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir, patch.dict(
            main.os.environ,
            {
                "APP_DB": str(Path(tempdir) / "auth.sqlite3"),
                "APP_PASSWORD": "original-password",
                "APP_SECRET": "fixed-session-secret",
            },
            clear=False,
        ):
            db.init_db()
            old_token = main.issue_auth_token(now=1_000)
            self.assertTrue(main.verify_auth_password("original-password"))
            response = Response()
            result = main.api_auth_change_password(
                main.PasswordChangeRequest(current_password="original-password", new_password="replacement-password"),
                response,
            )
            self.assertTrue(result["sessions_invalidated"])
            self.assertFalse(main.auth_session_valid(old_token, now=1_001))
            self.assertFalse(main.verify_auth_password("original-password"))
            self.assertTrue(main.verify_auth_password("replacement-password"))
            self.assertTrue(main.auth_session_valid(main.issue_auth_token(now=1_001), now=1_002))

    def test_rebuild_endpoint_only_enqueues_job(self) -> None:
        with patch.object(main, "create_job", return_value=42) as create_job:
            result = main.api_rebuild_media_index()
        create_job.assert_called_once_with("index-metadata")
        self.assertEqual(result["id"], 42)
        self.assertTrue(result["queued"])

    def test_semantic_endpoint_forwards_structured_ai_filters(self) -> None:
        understanding = {
            "parsed": {
                "semantic_query": "教室 JK 裸足",
                "media_type": "video",
                "author": "作者甲",
                "face_group": "FaceGroup_1",
                "favorite": "true",
                "has_subtitles": "true",
                "min_duration": 600.0,
                "max_duration": 1800.0,
                "resolution": "4K",
            },
            "intent": {"prefer": ["JK学生", "足交足控"]},
        }
        with patch.object(main, "understand_search_query", return_value=understanding), patch.object(
            main, "semantic_media_search", return_value={"items": []}
        ) as search:
            result = main.api_semantic_search(q="口语查询", limit=12)
        self.assertEqual(result, {"items": []})
        search.assert_called_once_with(
            q="教室 JK 裸足",
            media_type="video",
            author="作者甲",
            face_group="FaceGroup_1",
            favorite="true",
            has_subtitles="true",
            min_duration=600.0,
            max_duration=1800.0,
            resolution="4K",
            limit=12,
            intent={"prefer": ["JK学生", "足交足控"]},
        )


class ModelDownloadSecurityTests(unittest.TestCase):
    @staticmethod
    def _address(address: str):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443))]

    def test_private_and_credentialed_urls_are_rejected(self) -> None:
        with patch.object(model_manager.socket, "getaddrinfo", return_value=self._address("127.0.0.1")):
            with self.assertRaisesRegex(ValueError, "private"):
                model_manager.validate_download_url("https://models.example/model.onnx")
        with self.assertRaisesRegex(ValueError, "embedded credentials"):
            model_manager.validate_download_url("https://token:secret@models.example/model.onnx")

    def test_public_https_url_is_accepted_and_http_is_rejected_by_default(self) -> None:
        with patch.object(model_manager.socket, "getaddrinfo", return_value=self._address("93.184.216.34")):
            self.assertEqual(
                model_manager.validate_download_url("https://models.example/model.onnx"),
                "https://models.example/model.onnx",
            )
            with self.assertRaisesRegex(ValueError, "HTTPS"):
                model_manager.validate_download_url("http://models.example/model.onnx")

    def test_catalog_url_redacts_query_tokens(self) -> None:
        redacted = model_manager._redact_url("https://models.example/model.onnx?token=secret&sig=value#fragment")
        self.assertNotIn("secret", redacted)
        self.assertNotIn("value", redacted)
        self.assertNotIn("fragment", redacted)
        self.assertIn("REDACTED", redacted)

    def test_custom_source_requires_sha256(self) -> None:
        spec = {"url_env": "", "default_url": ""}
        settings = {model_manager.source_setting_key("custom"): "https://models.example/model.onnx"}
        with patch.object(model_manager.socket, "getaddrinfo", return_value=self._address("93.184.216.34")):
            with patch.dict(model_manager.os.environ, {"MODEL_REQUIRE_SHA256_CUSTOM": "true"}, clear=False):
                with self.assertRaisesRegex(RuntimeError, "SHA256"):
                    model_manager._download_configuration("custom", spec, settings)

    def test_bge_is_a_fixed_complete_snapshot(self) -> None:
        spec = model_manager.MODEL_REGISTRY["bge-small-text"]
        self.assertEqual(spec["kind"], "runtime-cache")
        self.assertEqual(spec["command"], "fixed-snapshot")
        self.assertEqual(spec["repo_id"], "onnx-community/bge-small-zh-v1.5-ONNX")
        self.assertTrue(spec["recommended"])
        self.assertEqual(spec["revision"], "18e2da99700c49ed48c0a0e3683da39348fbbb36")
        self.assertEqual(
            set(spec["required_files"]),
            {
                "config.json",
                "tokenizer.json",
                "tokenizer_config.json",
                "onnx/model_quantized.onnx",
                "onnx/model_quantized.onnx_data",
            },
        )

    def test_bge_source_cannot_be_replaced_through_custom_url_api(self) -> None:
        request = main.ModelSourceRequest(
            model_id="bge-small-text",
            url="https://models.example/untrusted.onnx",
            sha256="0" * 64,
        )
        with self.assertRaises(main.HTTPException) as raised:
            main.api_save_model_source(request)
        self.assertEqual(raised.exception.status_code, 400)

    def test_bge_snapshot_readiness_checks_every_required_file(self) -> None:
        spec = model_manager.MODEL_REGISTRY["bge-small-text"]
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for relative in spec["required_files"][:-1]:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"ready")
            self.assertEqual(model_manager._missing_required_files(root, spec), [spec["required_files"][-1]])
            final = root / spec["required_files"][-1]
            final.parent.mkdir(parents=True, exist_ok=True)
            final.write_bytes(b"ready")
            self.assertEqual(model_manager._missing_required_files(root, spec), [])

    def test_fixed_snapshot_rejects_any_other_repository(self) -> None:
        spec = dict(model_manager.MODEL_REGISTRY["bge-small-text"], repo_id="attacker/untrusted")
        with self.assertRaisesRegex(RuntimeError, "Unsupported"):
            model_manager._download_fixed_snapshot("bge-small-text", spec)

    def test_limited_copy_stops_before_writing_unbounded_output(self) -> None:
        class Source:
            def __init__(self) -> None:
                self.remaining = 3

            def read(self, _size: int) -> bytes:
                if not self.remaining:
                    return b""
                self.remaining -= 1
                return b"x" * 1024

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "model.part"
            with target.open("wb") as output:
                with self.assertRaisesRegex(RuntimeError, "configured limit"):
                    model_manager._copy_limited(Source(), output, 2048)
            self.assertLessEqual(target.stat().st_size, 2048)


if __name__ == "__main__":
    unittest.main()

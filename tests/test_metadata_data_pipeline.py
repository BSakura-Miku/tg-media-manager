from __future__ import annotations

import csv
import hashlib
import json
import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app import db, metadata


class TemporaryDatabaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.base = Path(self.tempdir.name)
        self.db_file = self.base / "app.sqlite3"
        self.env = patch.dict(
            os.environ,
            {
                "APP_DB": str(self.db_file),
                "MODEL_ROOT": str(self.base / "models"),
            },
            clear=False,
        )
        self.env.start()
        db.init_db()

    def tearDown(self) -> None:
        self.env.stop()
        self.tempdir.cleanup()

    def insert_media(self, root: Path, path: Path, media_type: str = "photo") -> int:
        with db.connect() as conn:
            conn.execute(
                """
                INSERT INTO media_items (path, root, relative_path, filename, ext, media_type, size_bytes, mtime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (str(path), str(root), str(path.relative_to(root)), path.name, path.suffix, media_type, path.stat().st_size, path.stat().st_mtime),
            )
            return int(conn.execute("SELECT id FROM media_items WHERE path=?", (str(path),)).fetchone()["id"])


class SemanticBackendTests(TemporaryDatabaseTestCase):
    def test_natural_parser_handles_media_negation_and_duration_direction(self) -> None:
        photos = metadata.parse_natural_search("不要收藏的图片")
        silent = metadata.parse_natural_search("不要字幕的视频")
        duration = metadata.parse_natural_search("不超过30秒的视频")
        self.assertEqual(photos["media_type"], "photo")
        self.assertEqual(photos["favorite"], "false")
        self.assertEqual(silent["media_type"], "video")
        self.assertEqual(silent["has_subtitles"], "false")
        self.assertIsNone(duration["min_duration"])
        self.assertEqual(duration["max_duration"], 30.0)

    def test_short_explicit_multi_facet_query_becomes_strict_and(self) -> None:
        with patch.object(metadata, "bge_intent_matches", return_value=[]):
            understood = metadata.understand_search_query("白丝学生口交")
            alternatives = metadata.understand_search_query("白丝学生或者口交")
        self.assertEqual(understood["provider"], "local-ontology-v2")
        self.assertEqual(understood["intent"]["must"], ["JK学生", "黑丝白丝", "口交"])
        self.assertEqual(alternatives["intent"]["must"], [])

    def test_colloquial_content_and_clothing_phrases_map_to_strict_intent(self) -> None:
        with patch.object(metadata, "bge_intent_matches", return_value=[]):
            understood = metadata.understand_search_query("教室里穿白色长袜的女学生帮男友用嘴服务")
        self.assertEqual(
            understood["intent"]["must"],
            ["JK学生", "黑丝白丝", "室内居家", "口交"],
        )

    def test_strict_intent_matches_earliest_filename_not_only_existing_tags(self) -> None:
        root = self.base / "intent-search"
        root.mkdir()
        exact = root / "exact.mp4"
        partial = root / "partial.mp4"
        exact.write_bytes(b"exact")
        partial.write_bytes(b"partial")
        exact_id = self.insert_media(root, exact, "video")
        partial_id = self.insert_media(root, partial, "video")
        vector = metadata.hashed_text_vector("白丝学生口交")
        with db.connect() as conn:
            conn.execute("UPDATE media_items SET original_name='白丝学生口交.mp4' WHERE id=?", (exact_id,))
            conn.execute("UPDATE media_items SET original_name='白丝学生.mp4' WHERE id=?", (partial_id,))
            conn.executemany(
                "INSERT INTO media_embeddings (media_id, kind, model, dim, vector, text) VALUES (?, 'text', 'local-hash-128', ?, ?, '')",
                [
                    (exact_id, len(vector), metadata.pack_vector(vector)),
                    (partial_id, len(vector), metadata.pack_vector(vector)),
                ],
            )
        with patch.object(metadata, "bge_intent_matches", return_value=[]), patch.object(
            metadata, "bge_text_vector", return_value=[]
        ), patch.object(metadata, "openclip_text_vector", return_value=([], "")):
            understood = metadata.understand_search_query("白丝学生口交")
            result = metadata.semantic_media_search(
                understood["parsed"]["semantic_query"], intent=understood["intent"], limit=10
            )
        self.assertFalse(result.get("relaxed_must"))
        self.assertEqual([item["id"] for item in result["items"]], [exact_id])

    def test_filename_classifier_persists_content_ontology(self) -> None:
        parsed = {"platform": "", "quality": "", "risk_state": "normal"}
        tags = metadata.tags_for("白丝学生口交骑乘.mp4", "videos/file.mp4", parsed)
        self.assertTrue({"JK学生", "黑丝白丝", "口交", "骑乘"}.issubset({item["tag"] for item in tags}))

    def test_bge_snapshot_uses_quantized_model_and_root_tokenizer(self) -> None:
        snapshot = self.base / "models" / "embeddings" / "bge-small"
        (snapshot / "onnx").mkdir(parents=True)
        model_path = snapshot / "onnx" / "model_quantized.onnx"
        tokenizer_path = snapshot / "tokenizer.json"
        model_path.write_bytes(b"onnx")
        tokenizer_path.write_text("{}", encoding="utf-8")
        with patch.object(metadata, "_registry_model_path", return_value=snapshot):
            selected_model, selected_tokenizer = metadata.bge_asset_paths()
        self.assertEqual(selected_model, model_path)
        self.assertEqual(selected_tokenizer, tokenizer_path)

    def test_bge_kind_is_only_used_when_real_vector_is_returned(self) -> None:
        with patch.object(metadata, "bge_text_vector", return_value=[0.6, 0.8]), patch.object(
            metadata, "_load_bge_backend", return_value={"model": "test-bge-onnx"}
        ):
            vector, kind, model = metadata.text_embedding("教室 JK")
        self.assertEqual(vector, [0.6, 0.8])
        self.assertEqual(kind, "bge_text")
        self.assertEqual(model, "test-bge-onnx")

    def test_missing_or_failed_bge_is_explicit_hash_fallback(self) -> None:
        with patch.object(metadata, "bge_text_vector", return_value=[]), patch.object(metadata, "_load_bge_backend", return_value=None):
            vector, kind, model = metadata.text_embedding("教室 JK")
            reported_kind, reported_model = metadata.embedding_kind_for_text()
        self.assertEqual(len(vector), 128)
        self.assertEqual((kind, model), ("text", "local-hash-128"))
        self.assertEqual((reported_kind, reported_model), ("text", "local-hash-128"))

    def test_rebuild_never_labels_hash_vector_as_bge(self) -> None:
        root = self.base / "fallback-index"
        root.mkdir()
        photo = root / "教室.jpg"
        photo.write_bytes(b"photo")
        self.insert_media(root, photo, "photo")
        with patch.object(metadata, "bge_text_vector", return_value=[]), patch.object(metadata, "_load_bge_backend", return_value=None):
            result = metadata.rebuild_semantic_index(root, mode="text")
        with db.connect() as conn:
            row = conn.execute("SELECT kind, model, dim FROM media_embeddings WHERE media_id=(SELECT id FROM media_items LIMIT 1) AND kind IN ('text', 'bge_text')").fetchone()
        self.assertTrue(result["ok"])
        self.assertEqual((row["kind"], row["model"], row["dim"]), ("text", "local-hash-128", 128))

    def test_semantic_rebuild_removes_stale_optional_embeddings(self) -> None:
        root = self.base / "semantic-reconcile"
        root.mkdir()
        video = root / "plain.mp4"
        video.write_bytes(b"video")
        media_id = self.insert_media(root, video, "video")
        vector = metadata.pack_vector([1.0])
        with db.connect() as conn:
            conn.executemany(
                """
                INSERT INTO media_embeddings (media_id, kind, model, dim, vector, text)
                VALUES (?, ?, 'stale', 1, ?, 'stale')
                """,
                [
                    (media_id, "tag", vector),
                    (media_id, "subtitle", vector),
                    (media_id, "image", vector),
                ],
            )
        with patch.object(metadata, "bge_text_vector", return_value=[]), patch.object(
            metadata, "_load_bge_backend", return_value=None
        ):
            result = metadata.rebuild_semantic_index(root)
        with db.connect() as conn:
            kinds = {
                row["kind"]
                for row in conn.execute(
                    "SELECT kind FROM media_embeddings WHERE media_id=?",
                    (media_id,),
                )
            }
        self.assertTrue(result["ok"])
        self.assertNotIn("tag", kinds)
        self.assertNotIn("subtitle", kinds)
        self.assertNotIn("image", kinds)

    def test_semantic_rebuild_replaces_stale_models_for_present_content(self) -> None:
        root = self.base / "semantic-model-reconcile"
        root.mkdir()
        video = root / "tagged.mp4"
        video.write_bytes(b"video")
        media_id = self.insert_media(root, video, "video")
        vector = metadata.pack_vector([1.0])
        with db.connect() as conn:
            conn.execute(
                "INSERT INTO media_tags (media_id, tag, category, source) VALUES (?, 'outdoor', 'scene', 'manual')",
                (media_id,),
            )
            conn.execute(
                "INSERT INTO media_transcripts (media_id, text) VALUES (?, 'hello world')",
                (media_id,),
            )
            conn.executemany(
                """
                INSERT INTO media_embeddings (media_id, kind, model, dim, vector, text)
                VALUES (?, ?, 'old-model', 1, ?, 'stale')
                """,
                [
                    (media_id, "tag", vector),
                    (media_id, "subtitle", vector),
                ],
            )
        with patch.object(metadata, "bge_text_vector", return_value=[]), patch.object(
            metadata, "_load_bge_backend", return_value=None
        ):
            metadata.rebuild_semantic_index(root, mode="text")
        with db.connect() as conn:
            rows = conn.execute(
                """
                SELECT kind, model
                FROM media_embeddings
                WHERE media_id=? AND kind IN ('tag', 'subtitle')
                ORDER BY kind, model
                """,
                (media_id,),
            ).fetchall()
        self.assertEqual(
            [(row["kind"], row["model"]) for row in rows],
            [("subtitle", "local-hash-128"), ("tag", "local-hash-128")],
        )


class MetadataIndexTests(TemporaryDatabaseTestCase):
    def test_rebuild_cleanup_is_scoped_to_requested_root(self) -> None:
        root_a = self.base / "a"
        root_b = self.base / "b"
        root_a.mkdir()
        root_b.mkdir()
        media_a = root_a / "one.jpg"
        media_b = root_b / "two.jpg"
        media_a.write_bytes(b"a")
        media_b.write_bytes(b"b")

        metadata.rebuild_metadata_index(root_a)
        metadata.rebuild_metadata_index(root_b)
        media_a.unlink()
        metadata.rebuild_metadata_index(root_a)

        with db.connect() as conn:
            roots = [row["root"] for row in conn.execute("SELECT root FROM media_items ORDER BY root")]
        self.assertEqual(roots, [str(root_b)])

    def test_face_groups_are_imported_and_diagnostics_are_unambiguous(self) -> None:
        root = self.base / "media"
        manifests = root / "_MANIFESTS"
        manifests.mkdir(parents=True)
        photo = root / "actor.jpg"
        photo.write_bytes(b"photo")
        metadata.rebuild_metadata_index(root)
        with (manifests / "face_groups.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["face_group", "media_path", "det_score"])
            writer.writeheader()
            writer.writerow({"face_group": "FaceGroup_000001", "media_path": "actor.jpg", "det_score": "0.92"})

        result = metadata.import_vision_outputs(root)
        diagnostics = metadata.media_index_diagnostics(root)
        with db.connect() as conn:
            tag = conn.execute("SELECT tag, category, source FROM media_tags WHERE category='face_group'").fetchone()

        self.assertEqual(result["face_group_tags"], 1)
        self.assertEqual(dict(tag), {"tag": "FaceGroup_000001", "category": "face_group", "source": "face-cluster"})
        self.assertEqual(diagnostics["media"]["face_group_rows"], 1)
        self.assertEqual(diagnostics["media"]["faces"], 1)

    def test_diagnostics_do_not_mix_counts_between_media_roots(self) -> None:
        root_a = self.base / "diagnostics-a"
        root_b = self.base / "diagnostics-b"
        root_a.mkdir()
        root_b.mkdir()
        video_a = root_a / "a.mp4"
        video_b = root_b / "b.mp4"
        video_a.write_bytes(b"a")
        video_b.write_bytes(b"b")
        self.insert_media(root_a, video_a, "video")
        media_b = self.insert_media(root_b, video_b, "video")
        with db.connect() as conn:
            conn.execute(
                "INSERT INTO media_tags (media_id, tag, category, source) VALUES (?, 'outdoor', 'vision', 'vision')",
                (media_b,),
            )
            conn.execute(
                "INSERT INTO media_transcripts (media_id, text, segments_json) VALUES (?, 'hello', ?)",
                (media_b, json.dumps([{"start": 1, "end": 2, "text": "hello"}])),
            )
            conn.execute(
                "INSERT INTO media_embeddings (media_id, kind, model, dim, vector) VALUES (?, 'subtitle', 'test', 1, ?)",
                (media_b, metadata.pack_vector([1.0])),
            )
            conn.execute(
                "INSERT INTO media_metadata (media_id, probe_status) VALUES (?, 'ok')",
                (media_b,),
            )

        diagnostics = metadata.media_index_diagnostics(root_a)
        coverage = {item["id"]: item["ready"] for item in diagnostics["coverage"]}
        self.assertEqual(diagnostics["media"]["timed_transcripts"], 0)
        self.assertEqual(diagnostics["media"]["vision_labels"], 0)
        self.assertEqual(diagnostics["media"]["metadata_rows"], 0)
        self.assertEqual(coverage["tags"], 0)
        self.assertEqual(coverage["transcripts"], 0)
        self.assertEqual(coverage["subtitle_vectors"], 0)

    def test_incremental_hash_backfill_writes_full_and_short_hash(self) -> None:
        root = self.base / "hashes"
        root.mkdir()
        path = root / "sample.mp4"
        content = b"hash me once"
        path.write_bytes(content)
        media_id = self.insert_media(root, path, "video")

        result = metadata.backfill_media_hashes(root)
        with db.connect() as conn:
            row = conn.execute("SELECT sha256, hash8 FROM media_items WHERE id=?", (media_id,)).fetchone()
        expected = hashlib.sha256(content).hexdigest()
        self.assertTrue(result["ok"])
        self.assertEqual(result["updated"], 1)
        self.assertEqual(row["sha256"], expected)
        self.assertEqual(row["hash8"], expected[:8])

    def test_rebuild_preserves_hash_and_earliest_original_name(self) -> None:
        root = self.base / "preserve"
        root.mkdir()
        path = root / "VID_20250101_010203_durNA_resNA_01234567.mp4"
        path.write_bytes(b"content")
        media_id = self.insert_media(root, path, "video")
        with db.connect() as conn:
            conn.execute(
                "UPDATE media_items SET original_name='telegram-original-name.mp4', sha256='fullhash', hash8='fullhash' WHERE id=?",
                (media_id,),
            )

        metadata.rebuild_metadata_index(root)
        with db.connect() as conn:
            row = conn.execute("SELECT original_name, sha256, hash8 FROM media_items WHERE id=?", (media_id,)).fetchone()
        self.assertEqual(row["original_name"], "telegram-original-name.mp4")
        self.assertEqual(row["sha256"], "fullhash")
        self.assertEqual(row["hash8"], "fullhash")

    def test_formatted_original_name_is_upgraded_from_move_history(self) -> None:
        root = self.base / "history"
        manifests = root / "_MANIFESTS"
        manifests.mkdir(parents=True)
        normalized = "VID_20250101_010203_durNA_resNA_01234567.mp4"
        path = root / normalized
        path.write_bytes(b"content")
        with (manifests / "applied_moves.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["original_path", "new_path"])
            writer.writeheader()
            writer.writerow({"original_path": "videos/最开始的文件名.mp4", "new_path": normalized})

        metadata.rebuild_metadata_index(root)
        with db.connect() as conn:
            original_name = conn.execute("SELECT original_name FROM media_items WHERE path=?", (str(path),)).fetchone()["original_name"]
        self.assertEqual(original_name, "最开始的文件名.mp4")

    def test_cached_clip_vectors_import_without_loading_openclip(self) -> None:
        root = self.base / "clip"
        manifests = root / "_MANIFESTS"
        manifests.mkdir(parents=True)
        photo = root / "sample.jpg"
        photo.write_bytes(b"photo")
        self.insert_media(root, photo, "photo")
        (manifests / "vision_embeddings.jsonl").write_text(
            json.dumps(
                {
                    "media_path": "sample.jpg",
                    "model": "ViT-L-14",
                    "pretrained": "laion2b_s32b_b82k",
                    "embedding": [1.0] * 768,
                }
            )
            + "\n",
            encoding="utf-8",
        )

        with patch.object(metadata, "_load_openclip_text_backend", side_effect=AssertionError("vision model must not load")):
            result = metadata.import_clip_embeddings(root)
        with db.connect() as conn:
            row = conn.execute("SELECT kind, model, dim FROM media_embeddings").fetchone()
        self.assertTrue(result["ok"])
        self.assertEqual(result["imported"], 1)
        self.assertEqual(row["kind"], "clip_image")
        self.assertEqual(row["model"], "openclip:ViT-L-14:laion2b_s32b_b82k")
        self.assertEqual(row["dim"], 768)

    def test_semantic_search_can_rank_cached_clip_vectors(self) -> None:
        root = self.base / "clip-search"
        root.mkdir()
        photo = root / "outdoor.jpg"
        photo.write_bytes(b"photo")
        media_id = self.insert_media(root, photo, "photo")
        with db.connect() as conn:
            conn.execute(
                "INSERT INTO media_embeddings (media_id, kind, model, dim, vector, text) VALUES (?, 'clip_image', ?, 2, ?, '')",
                (media_id, "openclip:ViT-L-14:laion2b_s32b_b82k", metadata.pack_vector([1.0, 0.0])),
            )
        with patch.object(metadata, "bge_text_vector", return_value=[]), patch.object(
            metadata,
            "openclip_text_vector",
            return_value=([1.0, 0.0], "openclip:ViT-L-14:laion2b_s32b_b82k"),
        ):
            result = metadata.semantic_media_search("室外", limit=10)
        self.assertTrue(result["semantic"])
        self.assertEqual(result["items"][0]["id"], media_id)
        self.assertGreater(result["items"][0]["semantic_score"], 1.0)


class TranscriptSelectionTests(TemporaryDatabaseTestCase):
    def test_missing_and_zero_length_segments_are_selected_for_rerun(self) -> None:
        root = self.base / "videos"
        root.mkdir()
        missing = root / "missing.mp4"
        invalid = root / "invalid.mp4"
        valid = root / "valid.mp4"
        for path in (missing, invalid, valid):
            path.write_bytes(b"video")
        missing_id = self.insert_media(root, missing, "video")
        invalid_id = self.insert_media(root, invalid, "video")
        valid_id = self.insert_media(root, valid, "video")
        with db.connect() as conn:
            conn.execute(
                "INSERT INTO media_transcripts (media_id, text, segments_json) VALUES (?, ?, ?)",
                (invalid_id, "text only", json.dumps([{"start": 0, "end": 0, "text": "text only"}])),
            )
            conn.execute(
                "INSERT INTO media_transcripts (media_id, text, segments_json) VALUES (?, ?, ?)",
                (valid_id, "timed", json.dumps([{"start": 1, "end": 2, "text": "timed"}])),
            )

        selected = {int(row["id"]) for row in metadata.transcription_candidates(root)}
        self.assertEqual(selected, {missing_id, invalid_id})
        self.assertTrue(metadata.transcript_needs_timed_rerun('[{"start": 0, "end": 0, "text": "x"}]'))
        self.assertFalse(metadata.transcript_needs_timed_rerun('[{"start": 0, "end": 1, "text": "x"}]'))
        self.assertFalse(metadata.transcript_needs_timed_rerun('[]', '', 'faster-whisper'))

    def test_failed_transcription_is_deferred_and_new_fingerprint_can_retry(self) -> None:
        root = self.base / "retry-videos"
        root.mkdir()
        video = root / "retry.mp4"
        video.write_bytes(b"video")
        media_id = self.insert_media(root, video, "video")
        row = metadata.transcription_candidates(root)[0]
        fingerprint = row["transcription_fingerprint"]
        with db.connect() as conn:
            metadata.record_transcription_started(conn, media_id, fingerprint, "stable-faster-whisper", "medium")
            metadata.record_transcription_failure(conn, media_id, fingerprint, "temporary failure")

        self.assertEqual(metadata.transcription_candidates(root), [])
        with db.connect() as conn:
            state = conn.execute(
                "SELECT status, attempt_count, next_retry_at FROM media_transcription_state WHERE media_id=?",
                (media_id,),
            ).fetchone()
            conn.execute(
                "UPDATE media_transcription_state SET next_retry_at=0 WHERE media_id=?",
                (media_id,),
            )
        self.assertEqual(state["status"], "retry")
        self.assertEqual(state["attempt_count"], 1)
        self.assertGreater(state["next_retry_at"], 0)
        self.assertEqual([item["id"] for item in metadata.transcription_candidates(root)], [media_id])

        with db.connect() as conn:
            metadata.record_transcription_started(conn, media_id, fingerprint, "stable-faster-whisper", "medium")
            metadata.record_transcription_failure(conn, media_id, fingerprint, "no audio", permanent=True)
        self.assertEqual(metadata.transcription_candidates(root), [])
        with patch.dict(os.environ, {"WHISPER_MODEL": "large-v3-turbo"}, clear=False):
            self.assertEqual([item["id"] for item in metadata.transcription_candidates(root)], [media_id])

    def test_successful_transcript_is_reselected_after_fingerprint_change(self) -> None:
        root = self.base / "fingerprint-success"
        root.mkdir()
        video = root / "success.mp4"
        video.write_bytes(b"video")
        media_id = self.insert_media(root, video, "video")
        with db.connect() as conn:
            media = dict(conn.execute("SELECT * FROM media_items WHERE id=?", (media_id,)).fetchone())
            conn.execute(
                "INSERT INTO media_transcripts (media_id, text, segments_json, source) VALUES (?, 'hello', ?, 'stable-faster-whisper')",
                (media_id, json.dumps([{"start": 1, "end": 2, "text": "hello"}])),
            )
            with patch.dict(os.environ, {"WHISPER_MODEL": "medium"}, clear=False):
                fingerprint = metadata.transcription_fingerprint(media)
            metadata.record_transcription_started(
                conn,
                media_id,
                fingerprint,
                "stable-faster-whisper",
                "medium",
            )
            metadata.record_transcription_succeeded(conn, media_id, fingerprint)

        with patch.dict(os.environ, {"WHISPER_MODEL": "medium"}, clear=False):
            self.assertEqual(metadata.transcription_candidates(root), [])
        with patch.dict(os.environ, {"WHISPER_MODEL": "large-v3-turbo"}, clear=False):
            self.assertEqual(
                [item["id"] for item in metadata.transcription_candidates(root)],
                [media_id],
            )

    def test_fingerprint_includes_audio_truncation_and_timed_subtitle_mode(self) -> None:
        row = {
            "path": "/media/sample.mp4",
            "size_bytes": 100,
            "mtime": 123,
            "sha256": "",
        }
        with patch.dict(
            os.environ,
            {"TRANSCRIBE_MAX_SECONDS": "30", "GENERATE_TIMED_SUBTITLES": "false"},
            clear=False,
        ):
            preview = metadata.transcription_fingerprint(row)
        with patch.dict(
            os.environ,
            {"TRANSCRIBE_MAX_SECONDS": "0", "GENERATE_TIMED_SUBTITLES": "true"},
            clear=False,
        ):
            full = metadata.transcription_fingerprint(row)
        self.assertNotEqual(preview, full)

    def test_fingerprint_normalizes_equivalent_configuration_values(self) -> None:
        row = {
            "path": "/media/sample.mp4",
            "size_bytes": 100,
            "mtime": 123,
            "sha256": "",
        }
        with patch.dict(
            os.environ,
            {
                "TRANSCRIPT_ENGINE": "stable-ts",
                "WHISPER_BEAM_SIZE": "05",
                "WHISPER_STABLE_TIMESTAMPS": "1",
                "SUBTITLE_MAX_SECONDS": "7",
            },
            clear=False,
        ):
            first = metadata.transcription_fingerprint(row)
        with patch.dict(
            os.environ,
            {
                "TRANSCRIPT_ENGINE": "stable-faster-whisper",
                "WHISPER_BEAM_SIZE": "5",
                "WHISPER_STABLE_TIMESTAMPS": "true",
                "SUBTITLE_MAX_SECONDS": "7.00",
            },
            clear=False,
        ):
            second = metadata.transcription_fingerprint(row)
        self.assertEqual(first, second)

    def test_explicit_whisper_load_failure_records_retry_backoff(self) -> None:
        root = self.base / "model-load-failure"
        root.mkdir()
        video = root / "sample.mp4"
        video.write_bytes(b"video")
        media_id = self.insert_media(root, video, "video")
        with patch.dict(
            os.environ,
            {"TRANSCRIPT_ENGINE": "stable-faster-whisper", "WHISPER_MODEL": "medium"},
            clear=False,
        ), patch.object(
            metadata,
            "load_faster_whisper_model",
            side_effect=RuntimeError("runtime missing"),
        ), patch.object(
            metadata,
            "sensevoice_command",
            return_value=None,
        ), patch.object(
            metadata,
            "funasr_nano_command",
            return_value=None,
        ):
            result = metadata.transcribe_videos(root, limit=1)

        with db.connect() as conn:
            state = conn.execute(
                """
                SELECT status, attempt_count, last_error, next_retry_at
                FROM media_transcription_state
                WHERE media_id=?
                """,
                (media_id,),
            ).fetchone()
        self.assertFalse(result["ok"])
        self.assertEqual(result["failed"], 1)
        self.assertEqual(state["status"], "retry")
        self.assertEqual(state["attempt_count"], 1)
        self.assertIn("runtime missing", state["last_error"])
        self.assertGreater(state["next_retry_at"], int(time.time()))

    def test_text_without_timestamps_is_saved_and_deferred(self) -> None:
        root = self.base / "untimed-result"
        root.mkdir()
        video = root / "sample.mp4"
        video.write_bytes(b"video")
        media_id = self.insert_media(root, video, "video")
        untimed_result = {
            "ok": True,
            "text": "recognized text",
            "tag_text": "recognized text",
            "language": "en",
            "segments": [{"start": 0, "end": 0, "text": "recognized text"}],
            "engine": "funasr-nano-onnx",
            "model": "/models/funasr-nano",
        }
        with patch.dict(
            os.environ,
            {
                "TRANSCRIPT_ENGINE": "funasr-nano-onnx",
                "GENERATE_TIMED_SUBTITLES": "true",
            },
            clear=False,
        ), patch.object(
            metadata,
            "funasr_nano_command",
            return_value=["funasr"],
        ), patch.object(
            metadata,
            "sensevoice_command",
            return_value=None,
        ), patch.object(
            metadata,
            "extract_audio_wav",
            return_value=(True, ""),
        ), patch.object(
            metadata,
            "audio_stream_start_offset",
            return_value=0.0,
        ), patch.object(
            metadata,
            "transcribe_with_funasr_nano_onnx",
            return_value=untimed_result,
        ), patch.object(
            metadata,
            "load_faster_whisper_model",
            side_effect=RuntimeError("timing fallback unavailable"),
        ):
            result = metadata.transcribe_videos(root, limit=1)
            deferred_candidates = metadata.transcription_candidates(root)

        with db.connect() as conn:
            state = conn.execute(
                """
                SELECT status, engine, model, last_error, next_retry_at
                FROM media_transcription_state
                WHERE media_id=?
                """,
                (media_id,),
            ).fetchone()
            transcript = conn.execute(
                "SELECT text FROM media_transcripts WHERE media_id=?",
                (media_id,),
            ).fetchone()
        self.assertEqual(transcript["text"], "recognized text")
        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(state["status"], "retry")
        self.assertEqual(state["engine"], "funasr-nano-onnx")
        self.assertEqual(state["model"], "/models/funasr-nano")
        self.assertIn("no usable timestamps", state["last_error"])
        self.assertGreater(state["next_retry_at"], int(time.time()))
        self.assertEqual(deferred_candidates, [])


class SchemaMigrationTests(unittest.TestCase):
    def test_old_tables_receive_idempotent_columns_and_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "legacy.sqlite3"
            conn = sqlite3.connect(path)
            conn.executescript(
                """
                CREATE TABLE jobs (id INTEGER PRIMARY KEY, command TEXT, status TEXT, progress INTEGER, message TEXT, created_at TEXT, stdout TEXT, stderr TEXT);
                CREATE TABLE media_items (id INTEGER PRIMARY KEY, path TEXT UNIQUE, filename TEXT);
                CREATE TABLE media_transcripts (media_id INTEGER PRIMARY KEY, text TEXT);
                """
            )
            conn.close()
            with patch.dict(os.environ, {"APP_DB": str(path)}, clear=False):
                db.init_db()
                db.init_db()
                with db.connect() as migrated:
                    jobs_columns = {row["name"] for row in migrated.execute("PRAGMA table_info(jobs)")}
                    media_columns = {row["name"] for row in migrated.execute("PRAGMA table_info(media_items)")}
                    transcript_columns = {
                        row["name"] for row in migrated.execute("PRAGMA table_info(media_transcripts)")
                    }
                    transcription_state_columns = {
                        row["name"]
                        for row in migrated.execute("PRAGMA table_info(media_transcription_state)")
                    }
                    version = migrated.execute("SELECT version FROM schema_version WHERE id=1").fetchone()["version"]
            self.assertIn("heartbeat_at", jobs_columns)
            self.assertIn("finished_at", jobs_columns)
            self.assertIn("sha256", media_columns)
            self.assertIn("root", media_columns)
            self.assertIn("quality_json", transcript_columns)
            self.assertIn("fingerprint", transcription_state_columns)
            self.assertIn("next_retry_at", transcription_state_columns)
            self.assertEqual(version, db.SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()

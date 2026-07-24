from __future__ import annotations

import csv
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.core import tg_media_library


FACE_INDEX_FIELDS = [
    "media_path",
    "frame_path",
    "face_index",
    "bbox",
    "area",
    "det_score",
    "embedding",
    "backend",
    "embedding_model",
    "embedding_space",
    "embedding_hash",
    "error",
]
LEGACY_FACE_INDEX_FIELDS = [
    "media_path",
    "frame_path",
    "face_index",
    "bbox",
    "area",
    "det_score",
    "embedding",
    "error",
]
FACE_GROUP_FIELDS = [
    "face_group",
    "media_path",
    "frame_path",
    "bbox",
    "area",
    "det_score",
    "representative_frame",
    "group_face_count",
    "group_media_count",
]
LEGACY_FACE_GROUP_FIELDS = [
    field for field in FACE_GROUP_FIELDS if field != "bbox"
]


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def face_index_row(
    *,
    media: str,
    frame: str,
    face_index: int,
    bbox: list[int],
    embedding: list[float],
    area: int = 100,
    backend: str = "insightface",
    model: str | None = None,
) -> dict:
    normalized = tg_media_library.normalized_face_embedding(embedding)
    resolved_model = model or tg_media_library.face_backend_model_name(backend)
    return {
        "media_path": media,
        "frame_path": frame,
        "face_index": str(face_index),
        "bbox": json.dumps(bbox),
        "area": str(area),
        "det_score": "0.99",
        "embedding": json.dumps(embedding),
        "backend": backend,
        "embedding_model": resolved_model,
        "embedding_space": tg_media_library.face_embedding_space_fingerprint(
            backend,
            resolved_model,
            len(embedding),
        ),
        "embedding_hash": tg_media_library.face_embedding_hash(normalized),
        "error": "",
    }


def face_group_row(*, group: str, face: dict, representative_frame: str) -> dict:
    return {
        "face_group": group,
        "media_path": face["media_path"],
        "frame_path": face["frame_path"],
        "bbox": face["bbox"],
        "area": face["area"],
        "det_score": face["det_score"],
        "representative_frame": representative_frame,
        "group_face_count": "1",
        "group_media_count": "1",
    }


def merge_record(group: str, embedding: list[float], space: tuple[str, ...]) -> dict:
    normalized = tg_media_library.normalized_face_embedding(embedding)
    if normalized is None:
        raise AssertionError("test embedding must be valid")
    return {
        "_group": group,
        "_group_row": {},
        "_embedding_vec": normalized,
        "_embedding_space_key": space,
    }


class FaceMergeSuggestionTests(unittest.TestCase):
    def test_same_frame_faces_use_their_own_bbox_embedding(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            manifests = root / "_MANIFESTS"
            manifests.mkdir()
            config = tg_media_library.Config(root=root)
            first = face_index_row(
                media="scene.mp4",
                frame="_frames/scene/frame_01.jpg",
                face_index=0,
                bbox=[0, 0, 100, 100],
                embedding=[1.0, 0.0],
            )
            second = face_index_row(
                media="scene.mp4",
                frame="_frames/scene/frame_01.jpg",
                face_index=1,
                bbox=[120, 0, 220, 100],
                embedding=[0.6, 0.8],
            )
            write_csv(manifests / "face_index.csv", FACE_INDEX_FIELDS, [first, second])
            write_csv(
                manifests / "face_groups.csv",
                FACE_GROUP_FIELDS,
                [
                    face_group_row(group="FaceGroup_000001", face=first, representative_frame=first["frame_path"]),
                    face_group_row(group="FaceGroup_000002", face=second, representative_frame=second["frame_path"]),
                ],
            )

            tg_media_library.write_face_merge_suggestions(config)

            suggestions = list(tg_media_library.dict_rows_from_csv(manifests / "face_merge_suggestions.csv"))
            self.assertEqual(len(suggestions), 1)
            self.assertEqual(
                set(suggestions[0]),
                {
                    "left_group",
                    "right_group",
                    "distance",
                    "left_media",
                    "right_media",
                    "left_frame",
                    "right_frame",
                },
            )
            self.assertAlmostEqual(float(suggestions[0]["distance"]), math.sqrt(0.8), places=6)
            self.assertNotEqual(suggestions[0]["distance"], "0.000000")

    def test_legacy_missing_columns_and_bbox_formatting_remain_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            manifests = root / "_MANIFESTS"
            manifests.mkdir()
            config = tg_media_library.Config(root=root)
            first = face_index_row(
                media="legacy-a.mp4",
                frame="_frames/legacy-a/frame_01.jpg",
                face_index=0,
                bbox=[0, 0, 100, 100],
                embedding=[1.0, 0.0],
            )
            second = face_index_row(
                media="legacy-b.mp4",
                frame="_frames/legacy-b/frame_01.jpg",
                face_index=0,
                bbox=[0, 0, 100, 100],
                embedding=[0.6, 0.8],
            )
            legacy_rows = [
                {field: row[field] for field in LEGACY_FACE_INDEX_FIELDS}
                for row in (first, second)
            ]
            write_csv(manifests / "face_index.csv", LEGACY_FACE_INDEX_FIELDS, legacy_rows)
            first_group = face_group_row(
                group="FaceGroup_000001",
                face=first,
                representative_frame=first["frame_path"],
            )
            first_group["bbox"] = "[0,0,100.0,100]"
            second_group = face_group_row(
                group="FaceGroup_000002",
                face=second,
                representative_frame=second["frame_path"],
            )
            write_csv(
                manifests / "face_groups.csv",
                FACE_GROUP_FIELDS,
                [first_group, second_group],
            )

            tg_media_library.write_face_merge_suggestions(config)

            suggestions = list(tg_media_library.dict_rows_from_csv(manifests / "face_merge_suggestions.csv"))
            self.assertEqual(len(suggestions), 1)
            self.assertAlmostEqual(float(suggestions[0]["distance"]), math.sqrt(0.8), places=6)

    def test_legacy_group_without_bbox_uses_only_unambiguous_frame(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            manifests = root / "_MANIFESTS"
            manifests.mkdir()
            config = tg_media_library.Config(root=root)
            first = face_index_row(
                media="legacy-a.mp4",
                frame="_frames/legacy-a/frame_01.jpg",
                face_index=0,
                bbox=[0, 0, 100, 100],
                embedding=[1.0, 0.0],
            )
            second = face_index_row(
                media="legacy-b.mp4",
                frame="_frames/legacy-b/frame_01.jpg",
                face_index=0,
                bbox=[0, 0, 100, 100],
                embedding=[0.6, 0.8],
            )
            write_csv(manifests / "face_index.csv", FACE_INDEX_FIELDS, [first, second])
            group_rows = [
                face_group_row(group="FaceGroup_000001", face=first, representative_frame=first["frame_path"]),
                face_group_row(group="FaceGroup_000002", face=second, representative_frame=second["frame_path"]),
            ]
            write_csv(
                manifests / "face_groups.csv",
                LEGACY_FACE_GROUP_FIELDS,
                [
                    {field: row[field] for field in LEGACY_FACE_GROUP_FIELDS}
                    for row in group_rows
                ],
            )

            tg_media_library.write_face_merge_suggestions(config)

            suggestions = list(tg_media_library.dict_rows_from_csv(manifests / "face_merge_suggestions.csv"))
            self.assertEqual(len(suggestions), 1)
            self.assertAlmostEqual(float(suggestions[0]["distance"]), math.sqrt(0.8), places=6)

    def test_malformed_bbox_with_multiple_faces_is_skipped_instead_of_guessed(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            manifests = root / "_MANIFESTS"
            manifests.mkdir()
            config = tg_media_library.Config(root=root)
            first = face_index_row(
                media="broken.mp4",
                frame="_frames/broken/frame_01.jpg",
                face_index=0,
                bbox=[0, 0, 100, 100],
                embedding=[1.0, 0.0],
            )
            second = face_index_row(
                media="broken.mp4",
                frame="_frames/broken/frame_01.jpg",
                face_index=1,
                bbox=[120, 0, 220, 100],
                embedding=[0.6, 0.8],
            )
            first["bbox"] = "not-json"
            second["bbox"] = "not-json"
            write_csv(manifests / "face_index.csv", FACE_INDEX_FIELDS, [first, second])
            first_group = face_group_row(
                group="FaceGroup_000001",
                face=first,
                representative_frame=first["frame_path"],
            )
            second_group = face_group_row(
                group="FaceGroup_000002",
                face=second,
                representative_frame=second["frame_path"],
            )
            write_csv(
                manifests / "face_groups.csv",
                FACE_GROUP_FIELDS,
                [first_group, second_group],
            )

            tg_media_library.write_face_merge_suggestions(config)

            suggestions = list(tg_media_library.dict_rows_from_csv(manifests / "face_merge_suggestions.csv"))
            self.assertEqual(suggestions, [])

    def test_mixed_backends_do_not_generate_merge_suggestions(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            manifests = root / "_MANIFESTS"
            manifests.mkdir()
            config = tg_media_library.Config(root=root)
            first = face_index_row(
                media="insightface.mp4",
                frame="_frames/insightface/frame_01.jpg",
                face_index=0,
                bbox=[0, 0, 100, 100],
                embedding=[1.0, 0.0],
                backend="insightface",
            )
            second = face_index_row(
                media="dlib.mp4",
                frame="_frames/dlib/frame_01.jpg",
                face_index=0,
                bbox=[0, 0, 100, 100],
                embedding=[1.0, 0.0],
                backend="face_recognition",
            )
            write_csv(manifests / "face_index.csv", FACE_INDEX_FIELDS, [first, second])
            write_csv(
                manifests / "face_groups.csv",
                FACE_GROUP_FIELDS,
                [
                    face_group_row(group="FaceGroup_000001", face=first, representative_frame=first["frame_path"]),
                    face_group_row(group="FaceGroup_000002", face=second, representative_frame=second["frame_path"]),
                ],
            )

            tg_media_library.write_face_merge_suggestions(config)

            suggestions = list(tg_media_library.dict_rows_from_csv(manifests / "face_merge_suggestions.csv"))
            self.assertEqual(suggestions, [])

    def test_report_only_rebuild_does_not_change_groups_or_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            manifests = root / "_MANIFESTS"
            manifests.mkdir()
            config = tg_media_library.Config(root=root)
            face = face_index_row(
                media="actor.mp4",
                frame="_frames/actor/frame_01.jpg",
                face_index=0,
                bbox=[0, 0, 100, 100],
                embedding=[1.0, 0.0],
            )
            write_csv(manifests / "face_index.csv", FACE_INDEX_FIELDS, [face])
            write_csv(
                manifests / "face_groups.csv",
                FACE_GROUP_FIELDS,
                [face_group_row(group="FaceGroup_000042", face=face, representative_frame=face["frame_path"])],
            )
            write_csv(
                manifests / "face_aliases.csv",
                ["face_group", "actor_name", "note"],
                [{"face_group": "FaceGroup_000042", "actor_name": "Actor", "note": "manual"}],
            )
            groups_before = (manifests / "face_groups.csv").read_bytes()
            aliases_before = (manifests / "face_aliases.csv").read_bytes()

            tg_media_library.face_cluster_report(config)

            self.assertEqual((manifests / "face_groups.csv").read_bytes(), groups_before)
            self.assertEqual((manifests / "face_aliases.csv").read_bytes(), aliases_before)
            self.assertTrue((manifests / "face_cluster_report.csv").exists())
            self.assertTrue((manifests / "face_merge_suggestions.csv").exists())

    def test_representative_media_is_selected_from_the_representative_face_row(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            manifests = root / "_MANIFESTS"
            manifests.mkdir()
            config = tg_media_library.Config(root=root)
            non_representative = face_index_row(
                media="part-a.mp4",
                frame="_frames/a/frame_01.jpg",
                face_index=0,
                bbox=[0, 0, 50, 50],
                embedding=[0.0, 1.0],
                area=2_500,
            )
            representative = face_index_row(
                media="part-b.mp4",
                frame="_frames/b/frame_01.jpg",
                face_index=0,
                bbox=[0, 0, 100, 100],
                embedding=[1.0, 0.0],
                area=10_000,
            )
            other_face = face_index_row(
                media="part-b.mp4",
                frame="_frames/b/frame_01.jpg",
                face_index=1,
                bbox=[120, 0, 220, 100],
                embedding=[0.6, 0.8],
            )
            write_csv(
                manifests / "face_index.csv",
                FACE_INDEX_FIELDS,
                [non_representative, representative, other_face],
            )
            write_csv(
                manifests / "face_groups.csv",
                FACE_GROUP_FIELDS,
                [
                    face_group_row(
                        group="FaceGroup_000001",
                        face=non_representative,
                        representative_frame=representative["frame_path"],
                    ),
                    face_group_row(
                        group="FaceGroup_000001",
                        face=representative,
                        representative_frame=representative["frame_path"],
                    ),
                    face_group_row(
                        group="FaceGroup_000002",
                        face=other_face,
                        representative_frame=other_face["frame_path"],
                    ),
                ],
            )

            tg_media_library.write_face_merge_suggestions(config)

            suggestions = list(tg_media_library.dict_rows_from_csv(manifests / "face_merge_suggestions.csv"))
            self.assertEqual(len(suggestions), 1)
            self.assertEqual(suggestions[0]["left_media"], "part-b.mp4")
            self.assertEqual(suggestions[0]["left_frame"], representative["frame_path"])
            self.assertAlmostEqual(float(suggestions[0]["distance"]), math.sqrt(0.8), places=6)


class FaceClusteringTests(unittest.TestCase):
    def test_embedding_fingerprints_are_stable_and_model_specific(self) -> None:
        vector = tg_media_library.normalized_face_embedding([3.0, 4.0])
        self.assertIsNotNone(vector)
        self.assertEqual(
            tg_media_library.face_embedding_hash(vector),
            tg_media_library.face_embedding_hash(vector),
        )
        self.assertNotEqual(
            tg_media_library.face_embedding_space_fingerprint("insightface", "buffalo_l", 512),
            tg_media_library.face_embedding_space_fingerprint("insightface", "antelopev2", 512),
        )

    def test_cluster_deduplicates_faces_and_separates_embedding_spaces(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            manifests = root / "_MANIFESTS"
            manifests.mkdir()
            config = tg_media_library.Config(root=root)
            first = face_index_row(
                media="scene.mp4",
                frame="_frames/scene/frame_01.jpg",
                face_index=0,
                bbox=[0, 0, 100, 100],
                embedding=[1.0, 0.0],
            )
            duplicate = {**first}
            same_identity_space = face_index_row(
                media="other.mp4",
                frame="_frames/other/frame_01.jpg",
                face_index=0,
                bbox=[0, 0, 100, 100],
                embedding=[1.0, 0.0],
            )
            far_face = face_index_row(
                media="far.mp4",
                frame="_frames/far/frame_01.jpg",
                face_index=0,
                bbox=[0, 0, 100, 100],
                embedding=[0.0, 1.0],
            )
            other_backend = face_index_row(
                media="legacy.mp4",
                frame="_frames/legacy/frame_01.jpg",
                face_index=0,
                bbox=[0, 0, 100, 100],
                embedding=[1.0, 0.0],
                backend="face_recognition",
            )
            other_dimension = face_index_row(
                media="dimension.mp4",
                frame="_frames/dimension/frame_01.jpg",
                face_index=0,
                bbox=[0, 0, 100, 100],
                embedding=[1.0, 0.0, 0.0],
            )
            other_model = face_index_row(
                media="model.mp4",
                frame="_frames/model/frame_01.jpg",
                face_index=0,
                bbox=[0, 0, 100, 100],
                embedding=[1.0, 0.0],
                model="antelopev2",
            )
            zero_vector = face_index_row(
                media="invalid.mp4",
                frame="_frames/invalid/frame_01.jpg",
                face_index=0,
                bbox=[0, 0, 100, 100],
                embedding=[0.0, 0.0],
            )
            write_csv(
                manifests / "face_index.csv",
                FACE_INDEX_FIELDS,
                [
                    first,
                    duplicate,
                    same_identity_space,
                    far_face,
                    other_backend,
                    other_dimension,
                    other_model,
                    zero_vector,
                ],
            )

            tg_media_library.face_cluster(config, threshold=0.8)

            rows = list(tg_media_library.dict_rows_from_csv(manifests / "face_groups.csv"))
            self.assertEqual(len(rows), 6)
            by_media = {row["media_path"]: row["face_group"] for row in rows}
            self.assertEqual(by_media["scene.mp4"], by_media["other.mp4"])
            self.assertNotEqual(by_media["scene.mp4"], by_media["far.mp4"])
            self.assertNotEqual(by_media["scene.mp4"], by_media["legacy.mp4"])
            self.assertNotEqual(by_media["scene.mp4"], by_media["dimension.mp4"])
            self.assertNotEqual(by_media["scene.mp4"], by_media["model.mp4"])
            self.assertNotIn("invalid.mp4", by_media)
            self.assertEqual(len(set(by_media.values())), 5)

    def test_manual_merge_recomputes_representative_and_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            manifests = root / "_MANIFESTS"
            manifests.mkdir()
            config = tg_media_library.Config(root=root)
            first = face_index_row(
                media="first.mp4",
                frame="_frames/first/frame_01.jpg",
                face_index=0,
                bbox=[0, 0, 50, 50],
                embedding=[1.0, 0.0],
                area=2_500,
            )
            second = face_index_row(
                media="second.mp4",
                frame="_frames/second/frame_01.jpg",
                face_index=0,
                bbox=[0, 0, 100, 100],
                embedding=[1.0, 0.0],
                area=10_000,
            )
            write_csv(manifests / "face_index.csv", FACE_INDEX_FIELDS, [first, second])
            write_csv(
                manifests / "face_groups.csv",
                FACE_GROUP_FIELDS,
                [
                    face_group_row(group="FaceGroup_000001", face=first, representative_frame=first["frame_path"]),
                    face_group_row(group="FaceGroup_000002", face=second, representative_frame=second["frame_path"]),
                ],
            )

            tg_media_library.merge_face_groups(config, "FaceGroup_000002", "FaceGroup_000001")

            rows = list(tg_media_library.dict_rows_from_csv(manifests / "face_groups.csv"))
            self.assertEqual({row["face_group"] for row in rows}, {"FaceGroup_000001"})
            self.assertEqual({row["group_face_count"] for row in rows}, {"2"})
            self.assertEqual({row["group_media_count"] for row in rows}, {"2"})
            self.assertEqual(
                {row["representative_frame"] for row in rows},
                {second["frame_path"]},
            )


class FaceMergeSearchTests(unittest.TestCase):
    def test_numpy_search_matches_bruteforce_global_top_k_across_spaces(self) -> None:
        try:
            import numpy  # noqa: F401
        except Exception:
            self.skipTest("NumPy unavailable")
        records = []
        for index in range(80):
            angle = index * 0.071
            records.append(
                merge_record(
                    f"FaceGroup_{index:06d}",
                    [math.cos(angle), math.sin(angle)],
                    ("space-a" if index % 3 else "space-b",),
                )
            )
        expected = []
        for left_index, left in enumerate(records):
            for right_index in range(left_index + 1, len(records)):
                right = records[right_index]
                if left["_embedding_space_key"] != right["_embedding_space_key"]:
                    continue
                distance = tg_media_library.vector_distance(
                    left["_embedding_vec"],
                    right["_embedding_vec"],
                )
                if distance <= 0.95 + 1e-12:
                    expected.append((distance, left, right))
        expected.sort(key=lambda item: (item[0], item[1]["_group"], item[2]["_group"]))
        expected = expected[:20]

        actual = tg_media_library.top_face_merge_pairs(
            records,
            threshold=0.95,
            limit=20,
            block_size=16,
        )

        self.assertEqual(
            [(left["_group"], right["_group"]) for _distance, left, right in actual],
            [(left["_group"], right["_group"]) for _distance, left, right in expected],
        )
        for actual_item, expected_item in zip(actual, expected):
            self.assertAlmostEqual(actual_item[0], expected_item[0], places=12)

    def test_numpy_search_is_blockwise_bounded_and_stable_for_identical_vectors(self) -> None:
        try:
            import numpy  # noqa: F401
        except Exception:
            self.skipTest("NumPy unavailable")
        records = [
            merge_record(f"FaceGroup_{index:06d}", [1.0, 0.0, 0.0, 0.0], ("space",))
            for index in range(800)
        ]
        original_distance = tg_media_library.vector_distance
        with patch.object(tg_media_library, "vector_distance", wraps=original_distance) as distance:
            pairs = tg_media_library.top_face_merge_pairs(
                records,
                threshold=0.95,
                limit=300,
                block_size=64,
            )

        self.assertEqual(len(pairs), 300)
        self.assertTrue(all(item[0] == 0.0 for item in pairs))
        self.assertEqual(pairs[0][1]["_group"], "FaceGroup_000000")
        self.assertEqual(pairs[0][2]["_group"], "FaceGroup_000001")
        self.assertEqual(pairs[-1][1]["_group"], "FaceGroup_000000")
        self.assertEqual(pairs[-1][2]["_group"], "FaceGroup_000300")
        self.assertLessEqual(distance.call_count, math.ceil(len(records) / 64) * 300)

    def test_scalar_fallback_keeps_zero_threshold_pairs_and_space_isolation(self) -> None:
        threshold = 0.95
        cosine = 1.0 - threshold * threshold / 2.0
        boundary = [cosine, math.sqrt(1.0 - cosine * cosine)]
        records = [
            merge_record("FaceGroup_000001", [1.0, 0.0], ("space-a",)),
            merge_record("FaceGroup_000002", [1.0, 0.0], ("space-a",)),
            merge_record("FaceGroup_000003", boundary, ("space-a",)),
            merge_record("FaceGroup_000004", [1.0, 0.0], ("space-b",)),
        ]

        with patch.dict(sys.modules, {"numpy": None}):
            pairs = tg_media_library.top_face_merge_pairs(
                records,
                threshold=threshold,
                limit=10,
                block_size=16,
            )

        self.assertEqual(
            [(left["_group"], right["_group"]) for _distance, left, right in pairs],
            [
                ("FaceGroup_000001", "FaceGroup_000002"),
                ("FaceGroup_000001", "FaceGroup_000003"),
                ("FaceGroup_000002", "FaceGroup_000003"),
            ],
        )
        self.assertEqual(pairs[0][0], 0.0)
        self.assertAlmostEqual(pairs[1][0], threshold, places=12)
        self.assertAlmostEqual(pairs[2][0], threshold, places=12)


class FaceScanCompatibilityTests(unittest.TestCase):
    def test_scan_preserves_legacy_rows_and_adds_fingerprints_to_new_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            manifests = root / "_MANIFESTS"
            manifests.mkdir()
            config = tg_media_library.Config(root=root)
            (root / "legacy.mp4").write_bytes(b"legacy")
            (root / "current.mp4").write_bytes(b"current")
            frame_path = "_frames/current/frame_01.jpg"
            (root / frame_path).parent.mkdir(parents=True)
            (root / frame_path).write_bytes(b"frame")
            write_csv(
                manifests / "frame_index.csv",
                ["media_path", "cache_key", "kind", "frames", "frame_times", "contact_sheet", "error"],
                [{
                    "media_path": "current.mp4",
                    "cache_key": "current",
                    "kind": "video",
                    "frames": frame_path,
                    "frame_times": "1.0",
                    "contact_sheet": "",
                    "error": "",
                }],
            )
            legacy = face_index_row(
                media="legacy.mp4",
                frame="_frames/legacy/frame_01.jpg",
                face_index=0,
                bbox=[0, 0, 100, 100],
                embedding=[1.0, 0.0],
            )
            write_csv(
                manifests / "face_index.csv",
                LEGACY_FACE_INDEX_FIELDS,
                [{field: legacy[field] for field in LEGACY_FACE_INDEX_FIELDS}],
            )
            detection = {
                "face_index": 0,
                "bbox": [10, 20, 110, 120],
                "area": 10_000,
                "det_score": 0.99,
                "embedding": [0.6, 0.8],
            }

            with patch.object(tg_media_library, "load_face_backend", return_value=("insightface", object())), patch.object(
                tg_media_library,
                "detect_faces",
                return_value=[detection],
            ), patch.object(tg_media_library, "cancel_requested", return_value=False), patch.dict(
                tg_media_library.os.environ,
                {"INSIGHTFACE_MODEL": "buffalo_l"},
                clear=False,
            ):
                tg_media_library.face_scan(config, limit=None)

            rows = list(tg_media_library.dict_rows_from_csv(manifests / "face_index.csv"))
            by_media = {row["media_path"]: row for row in rows}
            self.assertEqual(set(by_media), {"legacy.mp4", "current.mp4"})
            self.assertEqual(by_media["legacy.mp4"]["embedding_model"], "")
            self.assertEqual(by_media["legacy.mp4"]["embedding_space"], "")
            self.assertEqual(by_media["legacy.mp4"]["embedding_hash"], "")
            self.assertEqual(by_media["current.mp4"]["embedding_model"], "buffalo_l")
            self.assertTrue(by_media["current.mp4"]["embedding_space"].startswith("face-space-v1:"))
            self.assertEqual(len(by_media["current.mp4"]["embedding_hash"]), 64)


if __name__ == "__main__":
    unittest.main()

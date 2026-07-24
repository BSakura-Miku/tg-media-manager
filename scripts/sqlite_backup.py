#!/usr/bin/env python3
"""Create and verify consistent SQLite backups without stopping the service.

The create command uses SQLite's online backup API, so committed pages that are
still present in a WAL file are included in the backup. Every backup is written
atomically, checksummed, and restored into a temporary database for validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


MANIFEST_SUFFIX = ".manifest.json"
FORMAT_VERSION = 1


class BackupError(RuntimeError):
    """Raised when a backup or restore validation cannot be completed safely."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_only_connection(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True, timeout=60)


def pragma_int(connection: sqlite3.Connection, name: str) -> int:
    row = connection.execute(f"PRAGMA {name}").fetchone()
    return int(row[0]) if row else 0


def application_schema_version(connection: sqlite3.Connection) -> int | None:
    table = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_version'"
    ).fetchone()
    if not table:
        return None
    row = connection.execute("SELECT version FROM schema_version WHERE id=1").fetchone()
    return int(row[0]) if row else None


def integrity_check(connection: sqlite3.Connection) -> list[str]:
    results = [str(row[0]) for row in connection.execute("PRAGMA integrity_check").fetchall()]
    if results != ["ok"]:
        raise BackupError(f"SQLite integrity_check failed: {results[:10]}")
    return results


def make_standalone(connection: sqlite3.Connection) -> None:
    """Ensure a restored file can be opened without companion WAL/SHM files."""
    row = connection.execute("PRAGMA journal_mode=DELETE").fetchone()
    if not row or str(row[0]).lower() != "delete":
        raise BackupError("Could not convert backup to standalone DELETE journal mode")


def fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.partial")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o600)
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def database_metadata(path: Path) -> dict[str, Any]:
    with read_only_connection(path) as connection:
        check = integrity_check(connection)
        return {
            "integrity_check": check[0],
            "page_count": pragma_int(connection, "page_count"),
            "page_size": pragma_int(connection, "page_size"),
            "user_version": pragma_int(connection, "user_version"),
            "application_schema_version": application_schema_version(connection),
        }


def restore_and_verify(backup_path: Path) -> dict[str, Any]:
    """Restore a backup into a temporary SQLite file and validate the result."""
    with tempfile.TemporaryDirectory(prefix="tgmm-sqlite-restore-") as temporary_dir:
        restored_path = Path(temporary_dir) / "restored.sqlite3"
        with read_only_connection(backup_path) as source, sqlite3.connect(restored_path) as destination:
            source.backup(destination, pages=1024, sleep=0.05)
            make_standalone(destination)
            restored_metadata = {
                "integrity_check": integrity_check(destination)[0],
                "page_count": pragma_int(destination, "page_count"),
                "page_size": pragma_int(destination, "page_size"),
                "user_version": pragma_int(destination, "user_version"),
                "application_schema_version": application_schema_version(destination),
            }
        return restored_metadata


def manifest_path_for(backup_path: Path) -> Path:
    return backup_path.with_name(f"{backup_path.name}{MANIFEST_SUFFIX}")


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupError(f"Could not read backup manifest {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise BackupError(f"Backup manifest is not a JSON object: {path}")
    return data


def verify_backup(backup_path: Path, manifest_path: Path | None = None) -> dict[str, Any]:
    backup_path = backup_path.expanduser().resolve()
    if not backup_path.is_file():
        raise BackupError(f"Backup file does not exist: {backup_path}")

    manifest_path = (manifest_path or manifest_path_for(backup_path)).expanduser().resolve()
    manifest = load_manifest(manifest_path)
    actual_size = backup_path.stat().st_size
    actual_sha256 = sha256_file(backup_path)

    expected_name = str(manifest.get("database_file") or "")
    expected_size = int(manifest.get("size_bytes") or -1)
    expected_sha256 = str(manifest.get("sha256") or "")
    if int(manifest.get("format_version") or 0) != FORMAT_VERSION:
        raise BackupError(f"Unsupported backup manifest format: {manifest.get('format_version')}")
    if expected_name != backup_path.name:
        raise BackupError(f"Manifest expects {expected_name!r}, not {backup_path.name!r}")
    if expected_size != actual_size:
        raise BackupError(f"Backup size mismatch: expected {expected_size}, got {actual_size}")
    if not expected_sha256 or expected_sha256.lower() != actual_sha256.lower():
        raise BackupError("Backup SHA256 mismatch")

    backup_metadata = database_metadata(backup_path)
    restored_metadata = restore_and_verify(backup_path)
    for key in ("page_count", "page_size", "user_version", "application_schema_version"):
        if backup_metadata[key] != restored_metadata[key]:
            raise BackupError(
                f"Temporary restore metadata mismatch for {key}: "
                f"{backup_metadata[key]} != {restored_metadata[key]}"
            )

    return {
        "ok": True,
        "backup": str(backup_path),
        "manifest": str(manifest_path),
        "sha256": actual_sha256,
        "size_bytes": actual_size,
        "integrity_check": backup_metadata["integrity_check"],
        "temporary_restore": restored_metadata,
    }


def default_backup_name(source_path: Path) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{source_path.stem}_{timestamp}_{uuid4().hex[:8]}.sqlite3"


def create_backup(source_path: Path, output_path: Path) -> dict[str, Any]:
    source_path = source_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    manifest_path = manifest_path_for(output_path)

    if not source_path.is_file():
        raise BackupError(f"Source database does not exist: {source_path}")
    if source_path == output_path:
        raise BackupError("Source database and backup path must be different")
    if output_path.exists() or manifest_path.exists():
        raise BackupError(f"Refusing to overwrite existing backup or manifest: {output_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = output_path.with_name(f".{output_path.name}.{uuid4().hex}.partial")
    output_published = False
    manifest_published = False
    try:
        with read_only_connection(source_path) as source, sqlite3.connect(temporary) as destination:
            source.backup(destination, pages=1024, sleep=0.05)
            source_user_version = pragma_int(source, "user_version")
            source_application_schema_version = application_schema_version(source)
            make_standalone(destination)
            backup_metadata = {
                "integrity_check": integrity_check(destination)[0],
                "page_count": pragma_int(destination, "page_count"),
                "page_size": pragma_int(destination, "page_size"),
                "user_version": pragma_int(destination, "user_version"),
                "application_schema_version": application_schema_version(destination),
            }
        if source_user_version != backup_metadata["user_version"]:
            raise BackupError(
                "Source user_version changed during backup; retry after the current migration finishes"
            )
        if source_application_schema_version != backup_metadata["application_schema_version"]:
            raise BackupError(
                "Application schema version changed during backup; retry after the current migration finishes"
            )

        temporary.chmod(0o600)
        fsync_file(temporary)
        os.replace(temporary, output_path)
        output_published = True
        fsync_directory(output_path.parent)

        manifest = {
            "format_version": FORMAT_VERSION,
            "created_at": utc_now(),
            "source_database": str(source_path),
            "database_file": output_path.name,
            "size_bytes": output_path.stat().st_size,
            "sha256": sha256_file(output_path),
            **backup_metadata,
        }
        write_json_atomic(manifest_path, manifest)
        manifest_published = True

        result = verify_backup(output_path, manifest_path)
        result["created_at"] = manifest["created_at"]
        return result
    except BaseException:
        temporary.unlink(missing_ok=True)
        if manifest_published:
            manifest_path.unlink(missing_ok=True)
        if output_published:
            output_path.unlink(missing_ok=True)
        raise


def smoke_test() -> dict[str, Any]:
    """Exercise WAL capture, checksum verification, and temporary restore."""
    with tempfile.TemporaryDirectory(prefix="tgmm-sqlite-backup-smoke-") as temporary_dir:
        root = Path(temporary_dir)
        source = root / "live.sqlite3"
        backup = root / "backups" / "smoke.sqlite3"
        with sqlite3.connect(source) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA wal_autocheckpoint=0")
            connection.execute("CREATE TABLE smoke_items(id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
            connection.commit()
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            connection.executemany(
                "INSERT INTO smoke_items(value) VALUES (?)",
                [(f"row-{index}",) for index in range(128)],
            )
            connection.commit()
            wal_path = source.with_name(f"{source.name}-wal")
            if not wal_path.is_file() or wal_path.stat().st_size == 0:
                raise BackupError("Smoke test could not create an active WAL")

            result = create_backup(source, backup)

        with read_only_connection(backup) as restored:
            row_count = int(restored.execute("SELECT COUNT(*) FROM smoke_items").fetchone()[0])
        if row_count != 128:
            raise BackupError(f"Smoke test restored {row_count} rows; expected 128")
        if backup.stat().st_mode & 0o777 != 0o600:
            raise BackupError("Smoke test backup permissions are not 0600")
        if manifest_path_for(backup).stat().st_mode & 0o777 != 0o600:
            raise BackupError("Smoke test manifest permissions are not 0600")
        return {
            "ok": True,
            "wal_capture": True,
            "restored_rows": row_count,
            "integrity_check": result["integrity_check"],
            "checksum_verified": True,
            "temporary_restore_verified": True,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create and verify an online SQLite backup")
    create.add_argument("--source", type=Path, required=True, help="Path to the live SQLite database")
    output = create.add_mutually_exclusive_group()
    output.add_argument("--output", type=Path, help="Exact backup file path")
    output.add_argument("--output-dir", type=Path, help="Directory for a timestamped backup")

    verify = subparsers.add_parser("verify", help="Verify checksum, integrity, and temporary restore")
    verify.add_argument("--backup", type=Path, required=True, help="Backup SQLite file")
    verify.add_argument("--manifest", type=Path, help="Manifest path; defaults beside the backup")

    subparsers.add_parser("smoke-test", help="Test WAL capture and restore in a temporary directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "create":
            source = args.source.expanduser().resolve()
            if args.output:
                output = args.output
            else:
                output_dir = args.output_dir or source.parent / "backups"
                output = output_dir / default_backup_name(source)
            result = create_backup(source, output)
        elif args.command == "verify":
            result = verify_backup(args.backup, args.manifest)
        else:
            result = smoke_test()
    except (BackupError, OSError, sqlite3.Error, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

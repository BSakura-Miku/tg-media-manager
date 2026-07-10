from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Iterable, Mapping


SCHEMA_VERSION = 3


TABLE_COLUMN_MIGRATIONS: dict[str, Mapping[str, str]] = {
    "jobs": {
        "stage": "TEXT NOT NULL DEFAULT ''",
        "current_item": "TEXT NOT NULL DEFAULT ''",
        "processed": "INTEGER NOT NULL DEFAULT 0",
        "total": "INTEGER NOT NULL DEFAULT 0",
        "success_count": "INTEGER NOT NULL DEFAULT 0",
        "failed_count": "INTEGER NOT NULL DEFAULT 0",
        "skipped_count": "INTEGER NOT NULL DEFAULT 0",
        "cancel_requested": "INTEGER NOT NULL DEFAULT 0",
        "heartbeat_at": "TEXT",
        "started_at": "TEXT",
        "finished_at": "TEXT",
    },
    "media_items": {
        "root": "TEXT NOT NULL DEFAULT ''",
        "relative_path": "TEXT NOT NULL DEFAULT ''",
        "original_name": "TEXT NOT NULL DEFAULT ''",
        "ext": "TEXT NOT NULL DEFAULT ''",
        "media_type": "TEXT NOT NULL DEFAULT 'other'",
        "size_bytes": "INTEGER NOT NULL DEFAULT 0",
        "mtime": "REAL NOT NULL DEFAULT 0",
        "sha256": "TEXT NOT NULL DEFAULT ''",
        "hash8": "TEXT NOT NULL DEFAULT ''",
        "width": "INTEGER",
        "height": "INTEGER",
        "duration": "REAL",
        "resolution": "TEXT NOT NULL DEFAULT ''",
        "author": "TEXT NOT NULL DEFAULT ''",
        "person": "TEXT NOT NULL DEFAULT ''",
        "platform": "TEXT NOT NULL DEFAULT ''",
        "series": "TEXT NOT NULL DEFAULT ''",
        "code": "TEXT NOT NULL DEFAULT ''",
        "scene": "TEXT NOT NULL DEFAULT ''",
        "quality": "TEXT NOT NULL DEFAULT ''",
        "source": "TEXT NOT NULL DEFAULT ''",
        "normalized_path": "TEXT NOT NULL DEFAULT ''",
        "risk_state": "TEXT NOT NULL DEFAULT 'normal'",
        "created_at": "TEXT NOT NULL DEFAULT ''",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
    },
    "media_tags": {
        "category": "TEXT NOT NULL DEFAULT ''",
        "confidence": "REAL NOT NULL DEFAULT 1.0",
        "source": "TEXT NOT NULL DEFAULT 'auto'",
        "state": "TEXT NOT NULL DEFAULT 'confirmed'",
        "created_at": "TEXT NOT NULL DEFAULT ''",
    },
    "media_operations": {
        "media_id": "INTEGER",
        "operation": "TEXT NOT NULL DEFAULT ''",
        "detail": "TEXT NOT NULL DEFAULT ''",
        "created_at": "TEXT NOT NULL DEFAULT ''",
    },
    "media_timeline_segments": {
        "media_id": "INTEGER NOT NULL DEFAULT 0",
        "start_seconds": "REAL NOT NULL DEFAULT 0",
        "end_seconds": "REAL NOT NULL DEFAULT 0",
        "label": "TEXT NOT NULL DEFAULT ''",
        "confidence": "REAL NOT NULL DEFAULT 0",
        "source": "TEXT NOT NULL DEFAULT 'auto'",
        "representative_frame": "TEXT NOT NULL DEFAULT ''",
        "created_at": "TEXT NOT NULL DEFAULT ''",
    },
    "similarity_groups": {
        "kind": "TEXT NOT NULL DEFAULT ''",
        "signature": "TEXT NOT NULL DEFAULT ''",
        "score": "REAL NOT NULL DEFAULT 1.0",
        "created_at": "TEXT NOT NULL DEFAULT ''",
    },
    "similarity_members": {
        "group_id": "INTEGER NOT NULL DEFAULT 0",
        "media_id": "INTEGER NOT NULL DEFAULT 0",
        "role": "TEXT NOT NULL DEFAULT 'candidate'",
        "score": "REAL NOT NULL DEFAULT 1.0",
        "detail": "TEXT NOT NULL DEFAULT ''",
    },
    "parser_templates": {
        "name": "TEXT NOT NULL DEFAULT ''",
        "pattern": "TEXT NOT NULL DEFAULT ''",
        "enabled": "INTEGER NOT NULL DEFAULT 1",
        "created_at": "TEXT NOT NULL DEFAULT ''",
    },
    "media_transcripts": {
        "media_id": "INTEGER NOT NULL DEFAULT 0",
        "language": "TEXT NOT NULL DEFAULT ''",
        "text": "TEXT NOT NULL DEFAULT ''",
        "segments_json": "TEXT NOT NULL DEFAULT '[]'",
        "model": "TEXT NOT NULL DEFAULT ''",
        "source": "TEXT NOT NULL DEFAULT 'faster-whisper'",
        "created_at": "TEXT NOT NULL DEFAULT ''",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
    },
    "media_metadata": {
        "media_id": "INTEGER NOT NULL DEFAULT 0",
        "width": "INTEGER",
        "height": "INTEGER",
        "duration": "REAL",
        "resolution": "TEXT NOT NULL DEFAULT ''",
        "codec": "TEXT NOT NULL DEFAULT ''",
        "frame_rate": "REAL",
        "bit_rate": "INTEGER",
        "container": "TEXT NOT NULL DEFAULT ''",
        "probe_status": "TEXT NOT NULL DEFAULT 'pending'",
        "probe_error": "TEXT NOT NULL DEFAULT ''",
        "probed_at": "TEXT NOT NULL DEFAULT ''",
    },
    "tag_feedback": {
        "media_id": "INTEGER NOT NULL DEFAULT 0",
        "tag": "TEXT NOT NULL DEFAULT ''",
        "category": "TEXT NOT NULL DEFAULT ''",
        "verdict": "INTEGER NOT NULL DEFAULT 0",
        "source": "TEXT NOT NULL DEFAULT 'manual'",
        "note": "TEXT NOT NULL DEFAULT ''",
        "created_at": "TEXT NOT NULL DEFAULT ''",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
    },
    "vision_calibrators": {
        "tag": "TEXT NOT NULL DEFAULT ''",
        "model_json": "TEXT NOT NULL DEFAULT '{}'",
        "category": "TEXT NOT NULL DEFAULT ''",
        "positive_count": "INTEGER NOT NULL DEFAULT 0",
        "negative_count": "INTEGER NOT NULL DEFAULT 0",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
    },
    "saved_searches": {
        "name": "TEXT NOT NULL DEFAULT ''",
        "filters_json": "TEXT NOT NULL DEFAULT '{}'",
        "created_at": "TEXT NOT NULL DEFAULT ''",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
    },
    "media_embeddings": {
        "media_id": "INTEGER NOT NULL DEFAULT 0",
        "kind": "TEXT NOT NULL DEFAULT ''",
        "model": "TEXT NOT NULL DEFAULT ''",
        "dim": "INTEGER NOT NULL DEFAULT 0",
        "vector": "BLOB",
        "text": "TEXT NOT NULL DEFAULT ''",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
    },
}


def db_path() -> Path:
    return Path(os.environ.get("APP_DB", "/data/tg_media_manager.sqlite3"))


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _ensure_columns(conn: sqlite3.Connection, table: str, columns: Mapping[str, str]) -> None:
    if not _table_exists(conn, table):
        return
    existing = {str(row["name"]) for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()}
    for column, definition in columns.items():
        if column not in existing:
            conn.execute(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {definition}')


def migrate_schema(conn: sqlite3.Connection) -> None:
    """Apply additive, idempotent migrations to every persisted application table."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            id INTEGER PRIMARY KEY CHECK (id=1),
            version INTEGER NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    for table, columns in TABLE_COLUMN_MIGRATIONS.items():
        _ensure_columns(conn, table, columns)
    conn.execute(
        """
        INSERT INTO schema_version (id, version, updated_at)
        VALUES (1, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET version=excluded.version, updated_at=CURRENT_TIMESTAMP
        """,
        (SCHEMA_VERSION,),
    )


def init_db() -> None:
    with connect() as conn:
        # Older installations may be missing columns referenced by indexes below.
        # Run the additive pass before and after table creation so both old and new
        # databases converge on the same schema safely.
        migrate_schema(conn)
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT NOT NULL,
                status TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0,
                message TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                started_at TEXT,
                finished_at TEXT,
                stdout TEXT NOT NULL DEFAULT '',
                stderr TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS media_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                root TEXT NOT NULL DEFAULT '',
                relative_path TEXT NOT NULL DEFAULT '',
                filename TEXT NOT NULL,
                original_name TEXT NOT NULL DEFAULT '',
                ext TEXT NOT NULL DEFAULT '',
                media_type TEXT NOT NULL DEFAULT 'other',
                size_bytes INTEGER NOT NULL DEFAULT 0,
                mtime REAL NOT NULL DEFAULT 0,
                sha256 TEXT NOT NULL DEFAULT '',
                hash8 TEXT NOT NULL DEFAULT '',
                width INTEGER,
                height INTEGER,
                duration REAL,
                resolution TEXT NOT NULL DEFAULT '',
                author TEXT NOT NULL DEFAULT '',
                person TEXT NOT NULL DEFAULT '',
                platform TEXT NOT NULL DEFAULT '',
                series TEXT NOT NULL DEFAULT '',
                code TEXT NOT NULL DEFAULT '',
                scene TEXT NOT NULL DEFAULT '',
                quality TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT '',
                normalized_path TEXT NOT NULL DEFAULT '',
                risk_state TEXT NOT NULL DEFAULT 'normal',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_media_items_type ON media_items(media_type);
            CREATE INDEX IF NOT EXISTS idx_media_items_author ON media_items(author);
            CREATE INDEX IF NOT EXISTS idx_media_items_source ON media_items(source);
            CREATE INDEX IF NOT EXISTS idx_media_items_quality ON media_items(quality);
            CREATE INDEX IF NOT EXISTS idx_media_items_risk ON media_items(risk_state);

            CREATE TABLE IF NOT EXISTS media_tags (
                media_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT '',
                confidence REAL NOT NULL DEFAULT 1.0,
                source TEXT NOT NULL DEFAULT 'auto',
                state TEXT NOT NULL DEFAULT 'confirmed',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (media_id, tag, source),
                FOREIGN KEY (media_id) REFERENCES media_items(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_media_tags_tag ON media_tags(tag);
            CREATE INDEX IF NOT EXISTS idx_media_tags_category ON media_tags(category);
            CREATE INDEX IF NOT EXISTS idx_media_tags_state ON media_tags(state);

            CREATE TABLE IF NOT EXISTS media_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_id INTEGER,
                operation TEXT NOT NULL,
                detail TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (media_id) REFERENCES media_items(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS media_timeline_segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_id INTEGER NOT NULL,
                start_seconds REAL NOT NULL DEFAULT 0,
                end_seconds REAL NOT NULL DEFAULT 0,
                label TEXT NOT NULL DEFAULT '',
                confidence REAL NOT NULL DEFAULT 0,
                source TEXT NOT NULL DEFAULT 'auto',
                representative_frame TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (media_id) REFERENCES media_items(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_media_timeline_media ON media_timeline_segments(media_id);

            CREATE TABLE IF NOT EXISTS similarity_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                signature TEXT NOT NULL,
                score REAL NOT NULL DEFAULT 1.0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(kind, signature)
            );

            CREATE TABLE IF NOT EXISTS similarity_members (
                group_id INTEGER NOT NULL,
                media_id INTEGER NOT NULL,
                role TEXT NOT NULL DEFAULT 'candidate',
                score REAL NOT NULL DEFAULT 1.0,
                detail TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (group_id, media_id),
                FOREIGN KEY (group_id) REFERENCES similarity_groups(id) ON DELETE CASCADE,
                FOREIGN KEY (media_id) REFERENCES media_items(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_similarity_members_media ON similarity_members(media_id);

            CREATE TABLE IF NOT EXISTS parser_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                pattern TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS media_transcripts (
                media_id INTEGER PRIMARY KEY,
                language TEXT NOT NULL DEFAULT '',
                text TEXT NOT NULL DEFAULT '',
                segments_json TEXT NOT NULL DEFAULT '[]',
                model TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'faster-whisper',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (media_id) REFERENCES media_items(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_media_transcripts_text ON media_transcripts(text);

            CREATE TABLE IF NOT EXISTS media_metadata (
                media_id INTEGER PRIMARY KEY,
                width INTEGER,
                height INTEGER,
                duration REAL,
                resolution TEXT NOT NULL DEFAULT '',
                codec TEXT NOT NULL DEFAULT '',
                frame_rate REAL,
                bit_rate INTEGER,
                container TEXT NOT NULL DEFAULT '',
                probe_status TEXT NOT NULL DEFAULT 'pending',
                probe_error TEXT NOT NULL DEFAULT '',
                probed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (media_id) REFERENCES media_items(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_media_metadata_status ON media_metadata(probe_status);
            CREATE INDEX IF NOT EXISTS idx_media_metadata_resolution ON media_metadata(resolution);

            CREATE TABLE IF NOT EXISTS tag_feedback (
                media_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT '',
                verdict INTEGER NOT NULL,
                source TEXT NOT NULL DEFAULT 'manual',
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (media_id, tag, category),
                FOREIGN KEY (media_id) REFERENCES media_items(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_tag_feedback_tag ON tag_feedback(tag);
            CREATE INDEX IF NOT EXISTS idx_tag_feedback_verdict ON tag_feedback(verdict);

            CREATE TABLE IF NOT EXISTS vision_calibrators (
                tag TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT '',
                model_json TEXT NOT NULL,
                positive_count INTEGER NOT NULL DEFAULT 0,
                negative_count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (tag, category)
            );

            CREATE TABLE IF NOT EXISTS saved_searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                filters_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS media_embeddings (
                media_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                model TEXT NOT NULL DEFAULT '',
                dim INTEGER NOT NULL DEFAULT 0,
                vector BLOB,
                text TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (media_id, kind, model),
                FOREIGN KEY (media_id) REFERENCES media_items(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_media_embeddings_kind ON media_embeddings(kind);
            """
        )
        migrate_schema(conn)


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict]:
    return [dict(row) for row in rows]


def get_settings() -> dict[str, str]:
    with connect() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {str(row["key"]): str(row["value"]) for row in rows}


def save_settings(values: dict[str, str]) -> None:
    with connect() as conn:
        for key, value in values.items():
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

# SQLite Backup And Recovery

TG Media Manager uses SQLite in WAL mode. Copying only
`tg_media_manager.sqlite3` while the service is running can omit committed
transactions that still exist in `tg_media_manager.sqlite3-wal`.

Use the bundled online backup tool instead:

```bash
python3 scripts/sqlite_backup.py create \
  --source data/tg_media_manager.sqlite3 \
  --output-dir data/backups
```

The command:

1. Reads the live database through SQLite's online backup API.
2. Writes the backup to an adjacent temporary file and atomically renames it.
3. Runs `PRAGMA integrity_check`.
4. Writes a mode-`0600` JSON manifest containing the file size and SHA256.
5. Restores the backup into a temporary SQLite database and checks it again.

Both the `.sqlite3` file and its `.manifest.json` file are required. Copy the
pair to independent storage after creation.

## Verify Before Restore

Verification is read-only for the saved backup:

```bash
python3 scripts/sqlite_backup.py verify \
  --backup data/backups/tg_media_manager_YYYYmmddTHHMMSSZ_ID.sqlite3
```

The command checks the manifest, checksum, database integrity, and a temporary
restore. It exits non-zero on any mismatch.

## Restore

1. Stop the TG Media Manager container.
2. Run the verification command above.
3. Keep the current database as a rollback copy.
4. Copy the verified backup to `data/tg_media_manager.sqlite3`.
5. Remove stale `tg_media_manager.sqlite3-wal` and
   `tg_media_manager.sqlite3-shm` files only while the container is stopped.
6. Start the container and verify `/api/health`, `/api/version`, login, media
   counts, and recent jobs.

Never overwrite the live database while the container is running.

## Automation

Schedule `create` from the NAS task scheduler, then move or replicate the
backup/manifest pair to another storage target. Use a retention policy suitable
for the library, for example seven daily, four weekly, and twelve monthly
copies. Treat manifests and database backups as sensitive because the database
contains the login password hash and library metadata.

The built-in smoke test exercises a live WAL and temporary restore without
touching production data:

```bash
python3 scripts/sqlite_backup.py smoke-test
```

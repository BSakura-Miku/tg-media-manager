# Release Candidate And Single-Deploy Gate

`VERSION` is the release version source. The current candidate is an RC and
must not be deployed to the NAS until its source is clean, tagged, tested, and
the exact built image passes isolated staging.

## Daily Gate

```bash
make check
```

This runs backend and frontend tests, Python compilation, the WAL backup and
temporary-restore smoke, frontend production build, version consistency,
Compose validation, and Dockerfile checks.

## Freeze A Release Candidate

1. Update `VERSION`, the frontend package metadata, and the NAS example image.
2. Commit every candidate file, including new tests and scripts.
3. Confirm the worktree has no modified or untracked files.
4. Create an exact RC tag such as `v1.5.6-rc.1`.
5. Run:

```bash
make release-gate
```

The release gate deliberately fails for a dirty worktree, untracked files, or
an untagged commit. Do not bypass it for a NAS release.

## Build Once

```bash
make release-build
```

The image tag contains the version and commit. OCI labels and `/api/version`
record the same version, revision, image name, and build time. After staging
starts, do not rebuild the image: promote that exact image ID or exported tar
with its SHA256.

## Prepare Isolated Staging

The staging Compose file never references the production media path. Its
defaults live below `.local/staging`, which is ignored by Git.

```bash
mkdir -p .local/staging/media .local/staging/data .local/staging/models

# Put only disposable test media in .local/staging/media.
# Restore a verified production backup COPY, never the live database, to:
# .local/staging/data/tg_media_manager.sqlite3

export TGMM_STAGING_IMAGE="tg-media-manager:1.5.6-rc.1-<commit>-amd64"
export STAGING_APP_PASSWORD="a-staging-only-password"
export STAGING_APP_SECRET="$(openssl rand -hex 32)"

docker compose -p tgmm-staging -f docker-compose.staging.yml up -d
```

Use a fixture containing at least one photo, one video, one timed-subtitle
video, authors, face groups, jobs, and manifests. The staging password and
secret must never reuse production values.

## Browser Route Matrix

At desktop and mobile viewports, directly load, refresh, navigate back/forward,
and inspect console/network errors for every route:

```text
#dashboard  #quickFind  #library  #randomFlow
#authors    #faces      #tagGraph #models
#diagnostics #jobs      #logs     #settings
```

Require zero unexpected 401/5xx responses and zero uncaught browser errors.
Also exercise login/logout, a photo detail, video playback, timed subtitles,
saved search create/delete, disposable metadata edits, queued job status/logs,
settings persistence, and password change/re-login.

The API contract gate should derive all FastAPI routes and fail when a route has
no test. Public endpoints must match the explicit auth allowlist; every other
API must return 401 before login and its declared success/4xx status with
fixture data after login.

## Rollback Drill

Before NAS deployment, prove both paths in staging:

- The previous image can start against a copy of the migrated database.
- The release candidate can start after restoring the verified pre-upgrade
  backup.

Record database schema and row counts before and after migration. A data
rollback loses changes made after the backup; state that window explicitly.

## Single NAS Deployment

Only after all gates pass:

1. Export the already-tested image and record its SHA256 and image ID.
2. Verify free space and confirm no queued/running job.
3. Create and verify an online DB backup.
4. Snapshot Compose and environment files with restricted permissions.
5. Retain the previous image ID/digest.
6. Verify the transferred image checksum, load it, and point Compose to the
   immutable version+commit tag.
7. Deploy once, then verify version, authentication, schema/counts, summary,
   diagnostics, jobs, static assets, media file, thumbnail, and subtitles.

If a required post-deploy check fails, use the rehearsed rollback. Do not build
or patch a new temporary image on the NAS.

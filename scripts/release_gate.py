#!/usr/bin/env python3
"""Validate release version metadata and, for releases, a clean Git source."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:-(?:alpha|beta|rc)\.\d+)?$")


class GateError(RuntimeError):
    pass


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise GateError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def package_versions() -> dict[str, str]:
    package = json.loads((ROOT / "frontend/package.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "frontend/package-lock.json").read_text(encoding="utf-8"))
    return {
        "frontend/package.json": str(package.get("version") or ""),
        "frontend/package-lock.json": str(lock.get("version") or ""),
        "frontend/package-lock.json packages['']": str(
            (lock.get("packages", {}).get("") or {}).get("version") or ""
        ),
    }


def nas_example_image() -> str:
    for line in (ROOT / ".env.nas.example").read_text(encoding="utf-8").splitlines():
        if line.startswith("TG_MEDIA_MANAGER_IMAGE="):
            return line.split("=", 1)[1].strip()
    raise GateError(".env.nas.example has no TG_MEDIA_MANAGER_IMAGE")


def version_checks() -> dict:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not SEMVER_RE.fullmatch(version):
        raise GateError(f"VERSION is not an accepted SemVer release candidate: {version!r}")

    versions = package_versions()
    mismatches = {path: value for path, value in versions.items() if value != version}
    if mismatches:
        raise GateError(f"Version metadata does not match VERSION={version}: {mismatches}")

    example_image = nas_example_image()
    if version not in example_image:
        raise GateError(
            f"NAS example image {example_image!r} does not contain VERSION={version}"
        )
    return {
        "version": version,
        "frontend_versions": versions,
        "nas_example_image": example_image,
    }


def source_checks(version: str) -> dict:
    status_lines = [
        line for line in run_git("status", "--porcelain", "--untracked-files=all").splitlines() if line
    ]
    if status_lines:
        preview = status_lines[:30]
        suffix = f" (+{len(status_lines) - len(preview)} more)" if len(status_lines) > len(preview) else ""
        raise GateError(
            "Release source is dirty or has untracked files; commit the complete candidate first: "
            + json.dumps(preview, ensure_ascii=False)
            + suffix
        )
    commit = run_git("rev-parse", "HEAD")
    describe = run_git("describe", "--always", "--exact-match", "HEAD")
    accepted_tags = {version, f"v{version}"}
    if describe not in accepted_tags:
        raise GateError(
            f"HEAD tag {describe!r} does not match VERSION={version}; "
            f"expected one of {sorted(accepted_tags)}"
        )
    return {"commit": commit, "tag": describe, "clean": True}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--release",
        action="store_true",
        help="also require a clean, fully tracked source and an exact Git tag",
    )
    args = parser.parse_args(argv)
    try:
        result = {"ok": True, **version_checks()}
        if args.release:
            result["source"] = source_checks(result["version"])
    except (GateError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

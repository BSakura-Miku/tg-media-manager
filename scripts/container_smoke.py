#!/usr/bin/env python3
"""Smoke-test a running TG Media Manager container without exposing secrets."""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import re
import sys
import time
import urllib.error
import urllib.request


def request(opener, url: str, *, method: str = "GET", body: dict | None = None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    return opener.open(
        urllib.request.Request(url, data=data, headers=headers, method=method),
        timeout=5,
    )


def json_request(opener, url: str, *, method: str = "GET", body: dict | None = None) -> dict:
    with request(opener, url, method=method, body=body) as response:
        data = json.loads(response.read().decode("utf-8"))
        if not isinstance(data, dict):
            raise RuntimeError(f"{url} did not return a JSON object")
        return data


def wait_for_health(opener, base_url: str, timeout: int) -> None:
    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        try:
            if json_request(opener, f"{base_url}/api/health").get("ok") is True:
                return
        except Exception as exc:
            last_error = str(exc)
        time.sleep(1)
    raise RuntimeError(f"container did not become healthy: {last_error}")


def expect_status(opener, url: str, expected: int, *, method: str = "GET") -> None:
    try:
        with request(opener, url, method=method) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    if status != expected:
        raise RuntimeError(f"{method} {url} returned {status}, expected {expected}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:18787")
    parser.add_argument("--password", required=True)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--startup-timeout", type=int, default=60)
    args = parser.parse_args(argv)

    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    try:
        wait_for_health(opener, args.base_url.rstrip("/"), args.startup_timeout)
        base = args.base_url.rstrip("/")
        version = json_request(opener, f"{base}/api/version")
        if version.get("app_version") != args.expected_version:
            raise RuntimeError(f"version mismatch: {version.get('app_version')!r}")
        if version.get("build_commit") != args.expected_commit:
            raise RuntimeError(f"commit mismatch: {version.get('build_commit')!r}")

        status = json_request(opener, f"{base}/api/auth/status")
        if not status.get("enabled") or status.get("authenticated"):
            raise RuntimeError("authentication boundary is not enabled and locked")
        expect_status(opener, f"{base}/api/summary", 401)

        login = json_request(
            opener,
            f"{base}/api/auth/login",
            method="POST",
            body={"password": args.password},
        )
        if not login.get("ok"):
            raise RuntimeError("login did not succeed")
        for path in (
            "/api/auth/status",
            "/api/summary",
            "/api/jobs?limit=5",
            "/api/commands",
            "/api/models",
            "/api/settings",
        ):
            with request(opener, f"{base}{path}") as response:
                if response.status != 200:
                    raise RuntimeError(f"{path} returned {response.status}")

        with request(opener, f"{base}/") as response:
            html = response.read().decode("utf-8")
        asset = re.search(r'(?:src|href)="(/assets/[^"]+)"', html)
        if not asset:
            raise RuntimeError("frontend index did not reference a built asset")
        with request(opener, f"{base}{asset.group(1)}") as response:
            if response.status != 200 or not response.read(1):
                raise RuntimeError("frontend asset was not served")

        json_request(opener, f"{base}/api/auth/logout", method="POST")
        expect_status(opener, f"{base}/api/summary", 401)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "version": args.expected_version,
                "commit": args.expected_commit,
                "health": True,
                "auth_boundary": True,
                "frontend_asset": True,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

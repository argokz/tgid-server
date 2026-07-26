#!/usr/bin/env python3
"""Verify that a deployed map-api exposes the full route set (not the legacy ~7).

Usage:
  set API_BASE=https://itwin.kz/map-api
  python scripts/verify_prod_routes.py

Exit 0 when route count >= MIN_ROUTES and required paths respond.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API_BASE = os.getenv("API_BASE", "https://itwin.kz/map-api").rstrip("/")
MIN_ROUTES = int(os.getenv("MIN_ROUTES", "80"))

REQUIRED = [
    "/health",
    "/openapi.json",
    "/api/v1/auth/login",
    "/api/technical-conditions",
    "/api/technical-conditions/balance",
    "/api/passports/diagnostics",
    "/api/reports/excel-types",
    "/api/defects",
    "/api/heat-losses/seasons",
    "/api/temperature-graphs/sources",
    "/piezometer/path",
]


def fetch(path: str, method: str = "GET") -> tuple[int, object]:
    url = f"{API_BASE}{path}"
    # Cloudflare often blocks default Python UA (error 1010)
    req = urllib.request.Request(
        url,
        method=method,
        headers={"User-Agent": "itwin-api-verify/1.0 (+tgid-app)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, body
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc)


def main() -> int:
    print(f"Checking {API_BASE}")
    status, openapi = fetch("/openapi.json")
    if status != 200 or not isinstance(openapi, dict):
        print(f"[FAIL] openapi.json HTTP {status}: {str(openapi)[:200]}")
        print("Likely outdated map-api (legacy 7-route build). Redeploy itwin-api.")
        return 1

    paths = openapi.get("paths") or {}
    count = len(paths)
    print(f"[{'OK' if count >= MIN_ROUTES else 'FAIL'}] openapi paths: {count} (min {MIN_ROUTES})")
    failed = 0 if count >= MIN_ROUTES else 1

    for path in REQUIRED:
        # POST-only routes may 405/422 on GET — treat those as present
        code, _ = fetch(path)
        ok = code not in {0, 404}
        print(f"[{'OK' if ok else 'FAIL'}] {path}: HTTP {code}")
        if not ok:
            failed += 1

    print("failed:", failed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

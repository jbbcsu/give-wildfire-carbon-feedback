#!/usr/bin/env python3
"""Validate the negative global-infrastructure feasibility screen."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ALLOWED = {"pass", "partial", "fail"}


def validate(document: dict) -> list[str]:
    errors: list[str] = []
    gates = document.get("required_gates")
    candidates = document.get("candidates")
    if document.get("schema_version") != "1.0.0":
        errors.append("schema_version must be 1.0.0")
    if not isinstance(gates, list) or not gates or len(gates) != len(set(gates)):
        errors.append("required_gates must be a nonempty unique list")
        gates = []
    if not isinstance(candidates, list) or not candidates:
        errors.append("candidates must be a nonempty list")
        candidates = []

    ids: set[str] = set()
    computed_ready: list[str] = []
    for index, candidate in enumerate(candidates):
        prefix = f"candidates[{index}]"
        candidate_id = candidate.get("id")
        if not isinstance(candidate_id, str) or not candidate_id:
            errors.append(f"{prefix}.id is required")
            continue
        if candidate_id in ids:
            errors.append(f"duplicate candidate id: {candidate_id}")
        ids.add(candidate_id)
        statuses = candidate.get("gates")
        if not isinstance(statuses, dict) or set(statuses) != set(gates):
            errors.append(f"{candidate_id}: gates must exactly match required_gates")
            continue
        bad = {key: value for key, value in statuses.items() if value not in ALLOWED}
        if bad:
            errors.append(f"{candidate_id}: invalid gate statuses {bad}")
        if statuses and all(value == "pass" for value in statuses.values()):
            computed_ready.append(candidate_id)
        if not candidate.get("source") or not candidate.get("license"):
            errors.append(f"{candidate_id}: source and license are required")
        if any(value != "pass" for value in statuses.values()) and not candidate.get("blocker"):
            errors.append(f"{candidate_id}: failed/partial gates require a blocker")

    declared_ready = document.get("ready_candidates")
    if declared_ready != computed_ready:
        errors.append(
            f"ready_candidates {declared_ready!r} does not match all-pass candidates "
            f"{computed_ready!r}"
        )
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_candidate_screen.py SCREEN.json", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    document = json.loads(path.read_text(encoding="utf-8"))
    errors = validate(document)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {len(document['candidates'])} candidates; 0 GIVE-ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

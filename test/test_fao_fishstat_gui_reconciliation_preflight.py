#!/usr/bin/env python3
"""Fail-closed tests for FishStat GUI/headless reconciliation preflight."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


root = Path(__file__).resolve().parents[1]
script = root / "scripts/reconcile_fao_fishstat_gui_export.py"


with tempfile.TemporaryDirectory() as temporary:
    temp = Path(temporary)
    missing_gui = temp / "missing_gui_export.csv"
    headless = temp / "headless.csv"
    headless.write_text("validated headless placeholder\n", encoding="utf-8")
    headless_hash = hashlib.sha256(headless.read_bytes()).hexdigest()
    validation = temp / "headless_validation.json"
    validation.write_text(
        json.dumps(
            {
                "schema": "fao_fishstat_capture_headless_export_validation_v1",
                "export": {"bytes": headless.stat().st_size, "sha256": headless_hash},
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--check-inputs-only",
            "--gui",
            str(missing_gui),
            "--headless",
            str(headless),
            "--headless-validation",
            str(validation),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "reconciliation_blocked"
    assert report["ready"] is False
    assert report["missing_inputs"] == ["gui_export"]
    assert report["validation_errors"] == []
    assert report["writes_performed"] is False
    assert report["gui_launched"] is False
    assert all(value is False for value in report["claim_gates"].values())
    assert not missing_gui.exists(), "preflight fabricated the missing GUI export"
    assert sorted(temp.iterdir()) == [headless, validation]

print("FishStat GUI reconciliation preflight tests passed")

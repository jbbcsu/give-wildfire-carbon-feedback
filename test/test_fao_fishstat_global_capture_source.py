#!/usr/bin/env python3
"""Synthetic tamper gates for the FAO FishStat observed-catch source contract."""
from __future__ import annotations

import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_fao_fishstat_global_capture_source import validate


root = Path(__file__).resolve().parents[1]
contract = root / "data/provenance/fao_fishstat_global_capture_2026_v1.toml"


def must_fail(old: str, new: str, message: str) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        tampered = Path(temporary) / "contract.toml"
        tampered.write_text(contract.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
        try:
            validate(tampered, root)
        except ValueError as error:
            assert message in str(error)
        else:
            raise AssertionError("changed source contract was accepted")


must_fail('workspace_version = "2026.1.0"', 'workspace_version = "2025.1.0"', "workspace version")
must_fail('license = "CC-BY-4.0"', 'license = "unknown"', "license")
must_fail("record_export_completed = false", "record_export_completed = true", "closed gate")

print("FAO FishStat global-capture source contract tests passed")

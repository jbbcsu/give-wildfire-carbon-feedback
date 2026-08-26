#!/usr/bin/env python3
"""Argument-gate tests for the aggregate-irrigation diagnostic wrapper."""
from __future__ import annotations

import subprocess
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT / "scripts" / "run_irrigation_basis_chunk.sh"


def run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), *arguments],
        cwd=PROJECT,
        capture_output=True,
        text=True,
        check=False,
    )


too_few = run()
assert too_few.returncode == 2
assert "Usage:" in too_few.stderr

missing = run("missing-noirr", "missing-firr", "missing-weights", "mai", "2012", "2016", "ok")
assert missing.returncode == 1
assert "Missing required input file" in missing.stderr

print("irrigation-basis chunk orchestrator argument-gate tests passed")

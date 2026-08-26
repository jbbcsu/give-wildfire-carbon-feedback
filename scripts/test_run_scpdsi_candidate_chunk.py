#!/usr/bin/env python3
"""Static and fail-closed checks for the scPDSI candidate wrapper."""
from __future__ import annotations

import subprocess
from pathlib import Path


script = Path(__file__).resolve().parent / "run_scpdsi_candidate_chunk.sh"
text = script.read_text(encoding="utf-8")
required = [
    "set -euo pipefail",
    "build_stage_scpdsi_partitions.sh",
    "combine_stage_scpdsi_partitions.py",
    "allocate_irrigation_scpdsi_basis.py",
    "validate_irrigation_scpdsi_basis.py",
    "--exclude-missing-drought-cells",
    "--exclude-missing-weight-cells",
]
for token in required:
    assert token in text, token
assert "evaluate_crop_response_models.py" not in text

result = subprocess.run(["bash", str(script)], capture_output=True, text=True)
assert result.returncode == 2
assert "Usage:" in result.stderr
subprocess.run(["bash", "-n", str(script)], check=True)

print("scPDSI candidate wrapper tests passed")

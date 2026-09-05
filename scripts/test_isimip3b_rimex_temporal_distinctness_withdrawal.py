#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


root = Path(__file__).resolve().parents[1]
record = json.loads((root / "data/provenance/isimip3b_rimex_temporal_distinctness_v1_withdrawal_20260904.json").read_text(encoding="utf-8"))
assert record["status"] == "withdrawn_invalid_template_unit_assumption"
for key in ("withdrawn_audit", "withdrawn_contract", "withdrawn_preregistration", "replacement_audit"):
    item = record[key]
    assert sha256(root / item["path"]) == item["sha256"]
for gate in ("dependence_fit_authorized", "fair_feature_response_authorized", "response_estimation_authorized", "damage_or_scc_authorized"):
    assert record[gate] is False

print("temporal distinctness withdrawal integrity test passed")

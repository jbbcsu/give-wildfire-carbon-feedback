#!/usr/bin/env python3
"""Independent schema and fail-closed tests for the welfare-bridge audit."""

from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/audit_fishmip_fao_welfare_bridge_readiness.py"
SPEC = importlib.util.spec_from_file_location("audit_fishmip_fao_welfare_bridge_readiness", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


with tempfile.TemporaryDirectory() as directory:
    panel = Path(directory) / "panel.csv.gz"
    fields = MODULE.STATIC_FIELDS + [item for year in range(1950, 2025) for item in (f"value_{year}", f"status_{year}")]
    row = {field: "" for field in fields}
    row.update({"source_record_id": "1", "measure_code": "Q_tlw", "unit": "t"})
    with gzip.open(panel, "wt", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerow(row)
    summary = MODULE.scan_fao_panel(panel)
    assert summary["records"] == 1
    assert summary["years"] == 75
    assert summary["economic_static_field_count"] == 0

    malformed = Path(directory) / "malformed.csv.gz"
    with gzip.open(malformed, "wt", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=MODULE.STATIC_FIELDS + ["value_1950"])
        writer.writeheader()
    try:
        MODULE.scan_fao_panel(malformed)
    except ValueError:
        pass
    else:
        raise AssertionError("unpaired annual value/status schema passed")

result = MODULE.audit(ROOT / "config/fishmip_fao_welfare_bridge_readiness_v1.toml")
assert result["status"] == "blocked_precise_external_bioeconomic_bridge_bundle_required"
assert result["resident_evidence"]["fishmip"]["common_finite_grid_cells"] == 40398
assert result["resident_evidence"]["fao"]["records"] == 27625
assert result["resident_evidence"]["fao"]["economic_static_field_count"] == 0
assert result["resident_evidence"]["historical_bridge"]["paths_beating_constant_holdout_benchmark"] == 0
assert result["decision"]["defensible_resident_coupling_available"] is False
assert len(result["external_data_request"]) == 5
assert all(result["forbidden_shortcuts"].values())
assert result["claim_gates"]["damage_or_scc_authorized"] is False

receipt_path = ROOT / "data/provenance/fishmip_fao_welfare_bridge_readiness_20260928.json"
if receipt_path.exists():
    saved = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert saved["resident_evidence"] == result["resident_evidence"]
    assert saved["external_data_request"] == result["external_data_request"]

print("FishMIP/FAO welfare bridge readiness tests passed")

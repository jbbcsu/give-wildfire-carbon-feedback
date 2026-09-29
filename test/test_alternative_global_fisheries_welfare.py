#!/usr/bin/env python3
"""Independent fail-closed tests for the alternative global welfare audit."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
import tempfile
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/audit_alternative_global_fisheries_welfare.py"
SPEC = importlib.util.spec_from_file_location("audit_alternative_global_fisheries_welfare", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

config_path = ROOT / "config/alternative_global_fisheries_welfare_audit_v1.toml"
config = tomllib.loads(config_path.read_text(encoding="utf-8"))
candidates, qualifying = MODULE.validate_candidates(config)
assert len(candidates) == 5
assert qualifying == []
assert any(item["consumer_surplus"] for item in candidates)
assert any("global" in item["geographic_coverage"].lower() for item in candidates)
assert not any(item["consumer_surplus"] and item["producer_surplus"] for item in candidates)

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "country.csv"
    fields = ["sovereign_iso3", "sovereign", "rcp", "scenario", "p_tot"]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerow({"sovereign_iso3": "AAA", "sovereign": "A", "rcp": "RCP45", "scenario": "No Adaptation", "p_tot": "1"})
    summary = MODULE.scan_country_csv(path)
    assert summary["rows"] == 1
    assert summary["profit_columns"] == ["p_tot"]
    assert summary["consumer_surplus_column"] is False
    assert summary["producer_surplus_column"] is False

    malformed = Path(directory) / "malformed.csv"
    malformed.write_text("country,value\nA,1\n", encoding="utf-8")
    try:
        MODULE.scan_country_csv(malformed)
    except ValueError:
        pass
    else:
        raise AssertionError("incomplete country schema passed")

bad = dict(config)
bad["candidates"] = [dict(item) for item in config["candidates"]]
for criterion in MODULE.BOOLEAN_CRITERIA:
    bad["candidates"][0][criterion] = True
_, unexpectedly_qualifying = MODULE.validate_candidates(bad)
assert unexpectedly_qualifying == [bad["candidates"][0]["id"]]

receipt_path = ROOT / "data/provenance/alternative_global_fisheries_welfare_audit_20260928.json"
if receipt_path.exists():
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["qualifying_candidates"] == []
    assert receipt["decision"]["coefficient_transfer_authorized"] is False
    assert receipt["decision"]["damage_or_scc_authorized"] is False
    assert receipt["closest_candidate_source_audit"]["surplus_term_hits"] == {
        term: 0 for term in MODULE.SURPLUS_TERMS
    }

print("Alternative global fisheries welfare audit tests passed")

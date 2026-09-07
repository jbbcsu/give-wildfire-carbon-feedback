#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path
import tomllib

from validate_global_continuous_geographic_cluster_result import validate_payload


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/global_continuous_geographic_cluster_v1.toml"
RESULT_PATH = ROOT / "data/provenance/global_continuous_geographic_cluster_audit_20260907.json"
RESOURCE_PATH = ROOT / "data/provenance/global_continuous_geographic_cluster_resource_20260907.json"
CONFIG = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
RESULT = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
RESOURCE = json.loads(RESOURCE_PATH.read_text(encoding="utf-8"))


def expect_failure(mutator, message: str) -> None:
    payload = copy.deepcopy(RESULT)
    mutator(payload)
    try:
        validate_payload(payload, CONFIG, ROOT)
    except ValueError as error:
        assert message in str(error), str(error)
    else:
        raise AssertionError(f"tampered result passed: {message}")


validated = validate_payload(RESULT, CONFIG, ROOT, RESULT_PATH, RESOURCE)
assert validated["status"] == "validated_exploratory_geographic_and_source_cluster_diagnostic"
assert validated["crops"]["maize"]["terminal_pairs"] == 57767
assert validated["crops"]["soy"]["terminal_pairs"] == 26004
assert validated["model_promotion_authorized"] is False

expect_failure(lambda value: value.update(model_promotion_authorized=True), "closed result gate")
expect_failure(lambda value: value["crops"]["maize"].update(unique_terminal_pairs=57766), "terminal support")
expect_failure(lambda value: value["crops"]["soy"]["pooled_metrics"]["quantity"].update(test_pairs=1), "pooled support")
expect_failure(lambda value: value["crops"]["maize"]["paired_rmse_contrasts"].pop("scpdsi_mean_minus_quantity"), "contrast set")
expect_failure(lambda value: value["crops"]["soy"].update(coefficients=[1.0]), "forbidden fitted detail")
expect_failure(lambda value: value["crops"]["maize"]["held_out_source_blocks_by_fold"].update({"0": 1}), "per-fold block support")

print("global continuous geographic/source-cluster result tamper tests passed")

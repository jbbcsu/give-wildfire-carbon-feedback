#!/usr/bin/env python3
"""Independently validate the frozen U.S. corn SPEI response result."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

import estimate_us_corn_spei_response as production

ROOT = Path(__file__).resolve().parents[2]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def check(condition: bool, message: str, checks: list[str]) -> None:
    if not condition:
        raise ValueError(message)
    checks.append(message)


def explicit_dummy_fit(frame: pd.DataFrame, feature: str, cfg: dict) -> np.ndarray:
    x, _names = production.design(frame, feature, cfg)
    county = pd.get_dummies(frame.county_geoid.astype(str), drop_first=True, dtype=float).to_numpy()
    state_year = pd.get_dummies(frame.state.astype(str) + "_" + frame.harvest_year.astype(str),
                                drop_first=True, dtype=float).to_numpy()
    design = np.column_stack([np.ones(len(frame)), x, county, state_year])
    beta, _residuals, _rank, _singular = np.linalg.lstsq(design, frame.log_yield.to_numpy(float), rcond=None)
    return beta[1:1 + x.shape[1]]


def validate(result_path: Path, resource_path: Path) -> dict:
    checks: list[str] = []
    result, resource = json.loads(result_path.read_text()), json.loads(resource_path.read_text())
    check(result["schema"] == "us_corn_spei_response_result_v1", "result schema", checks)
    check(result["status"] == "completed_historical_association_and_climate_transport", "result status", checks)
    check(result["support"] == {"rows": 6854, "counties": 360, "future_cases": 15}, "exact support", checks)
    check(result["gates"] == {"historical_association": True, "future_climate_transport": True,
                              "causal_claim": False, "damage": False, "scc": False}, "claim gates", checks)
    check(resource["status"] == "completed" and resource["returncode"] == 0, "bounded run completed", checks)
    check(resource["sampled_peak_group_rss_bytes"] <= 1024**3, "one GiB memory gate", checks)
    config_path = ROOT / result["config"]["path"]
    implementation_path = ROOT / result["implementation"]["path"]
    check(digest(config_path) == result["config"]["sha256"], "config identity", checks)
    check(digest(implementation_path) == result["implementation"]["sha256"], "implementation identity", checks)
    cfg, panel, future = production.load(config_path)
    features = cfg["models"]["spei_features"]
    check([item["feature"] for item in result["estimates"]] == features, "exact feature order", checks)
    check(sum(bool(item["primary"]) for item in result["estimates"]) == 1, "one fixed primary feature", checks)
    for item in result["estimates"]:
        feature = item["feature"]
        full = item["full"]
        check(full["rows"] == 6854 and full["counties"] == 360, f"full support {feature}", checks)
        check(len(item["leave_one_state_out_median_contrast"]) == 10, f"ten state deletions {feature}", checks)
        check(all(record["same_sign_as_full"] for record in item["leave_one_state_out_median_contrast"]),
              f"state-deletion sign stability {feature}", checks)
        check(len(item["future_climate_transport"]) == 15, f"future case count {feature}", checks)
        for contrast in full["contrasts"]:
            check(set(contrast["standard_errors_log_yield"]) == {"county_cr1", "spatial_250km", "spatial_500km"},
                  f"inference family {feature}", checks)
            check(all(value > 0 and np.isfinite(value) for value in contrast["standard_errors_log_yield"].values()),
                  f"finite positive inference {feature}", checks)
    primary = next(item for item in result["estimates"] if item["primary"])
    independent_beta = explicit_dummy_fit(panel, primary["feature"], cfg)
    saved_beta = np.asarray(primary["full"]["beta"], float)
    check(float(np.max(np.abs(independent_beta - saved_beta))) < 2e-8,
          "explicit-dummy primary coefficients reproduce absorbed fit", checks)
    transported = production.transport(panel, future, primary["feature"], primary["full"])
    saved = {(item["model"], item["scenario"]): item for item in primary["future_climate_transport"]}
    for item in transported:
        prior = saved[(item["model"], item["scenario"])]
        check(abs(item["equal_county_mean_percent_yield_change"]
                  - prior["equal_county_mean_percent_yield_change"]) < 1e-12,
              f"primary future transport {item['model']} {item['scenario']}", checks)
    return {"schema": "us_corn_spei_response_validation_v1", "status": "passed", "checks": len(checks),
            "result": {"path": str(result_path.relative_to(ROOT)), "sha256": digest(result_path)},
            "resource": {"path": str(resource_path.relative_to(ROOT)), "sha256": digest(resource_path),
                         "sampled_peak_group_rss_bytes": resource["sampled_peak_group_rss_bytes"]},
            "validated": {"rows": len(panel), "counties": int(panel.county_geoid.nunique()),
                          "features": len(features), "future_cases": 15,
                          "primary_feature": primary["feature"]},
            "gates": result["gates"],
            "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)),
                               "sha256": digest(Path(__file__))}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--resource", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result_path = production.resolve(str(args.result)); resource_path = production.resolve(str(args.resource))
    output = production.resolve(str(args.output))
    check(not output.exists(), "fresh validation output required", [])
    validation = validate(result_path, resource_path)
    output.write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": validation["status"], "checks": validation["checks"],
                      "validated": validation["validated"]}))


if __name__ == "__main__":
    main()

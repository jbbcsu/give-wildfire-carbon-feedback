#!/usr/bin/env python3
"""Audit source provenance and scientific claim gates; emit a deterministic receipt."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def all_tokens(text, groups):
    lowered = text.lower()
    return {label: all(token.lower() in lowered for token in tokens) for label, tokens in groups.items()}


def run_audit(write=True):
    config_path = ROOT / "config/infectious_disease_readiness_v1.json"
    manifest_path = ROOT / "provenance/source_manifest_v1.json"
    config = json.loads(config_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    files = []
    for item in manifest["files"]:
        path = ROOT / item["path"]
        files.append({
            "path": item["path"],
            "exists": path.exists(),
            "size_ok": path.exists() and path.stat().st_size == item["bytes"],
            "sha256_ok": path.exists() and sha256(path) == item["sha256"],
        })
    fit = (ROOT / "data/source/scripts/10_fit_main.R").read_text()
    projection = (ROOT / "data/source/scripts/14_dengue_projections.R").read_text()
    estimator_checks = all_tokens(fit, {
        "ppml_fixed_effect_estimator": ["fepois"],
        "temperature_cubic_lags": ["mean_2m_air_temp_degree1_lag1", "mean_2m_air_temp_degree2_lag1", "mean_2m_air_temp_degree3_lag1", "mean_2m_air_temp_degree3_lag3"],
        "precipitation_controls": ["total_precipitation_lag1", "total_precipitation_lag2", "total_precipitation_lag3"],
        "population_weights": ["weights =~pop"],
        "unit_year_month_fixed_effects": ["countryfe^id", "countryfe^year", "countryfe^month"],
    })
    projection_checks = all_tokens(projection, {
        "uses_bootstrap_coefficients": ["main_coef_blockboot1000.rds"],
        "uses_population": ["all_pop2015.rds"],
        "uses_unit_covariates": ["unit_covariates.rds"],
        "scenario_contrast_not_marginal_pulse": ["ssp370", "ssp126"],
        "projects_cases": ["raw_case_dengue_change", "gbd_scaled_case_dengue_change"],
    })
    gates = config["claim_gates"]
    release_invariant_ok = gates["additive_scc_allowed"] == all([
        gates["matched_give_baseline_and_one_ton_pulse"],
        gates["morbidity_valuation_primary_source_pinned"],
        gates["mortality_overlap_resolved"],
        gates["labor_overlap_resolved"],
        gates["independent_replication_or_validation"],
        gates["discounting_and_currency_normalization_validated"],
    ])
    receipt = {
        "schema_version": "1.0",
        "source_files_verified": all(x["exists"] and x["size_ok"] and x["sha256_ok"] for x in files),
        "file_checks": files,
        "estimator_checks": estimator_checks,
        "projection_checks": projection_checks,
        "release_invariant_ok": release_invariant_ok,
        "additive_scc_allowed": gates["additive_scc_allowed"],
        "interpretation": "Published climate-incidence bridge is source-verified; SCC release remains closed.",
    }
    receipt["audit_pass"] = (
        receipt["source_files_verified"]
        and all(estimator_checks.values())
        and all(projection_checks.values())
        and release_invariant_ok
        and not gates["additive_scc_allowed"]
    )
    if write:
        output = ROOT / "results/readiness_receipt_v1.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        print(json.dumps(receipt, indent=2, sort_keys=True))
    return receipt


if __name__ == "__main__":
    result = run_audit()
    raise SystemExit(0 if result["audit_pass"] else 1)

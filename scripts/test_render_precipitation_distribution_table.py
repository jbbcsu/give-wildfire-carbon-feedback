#!/usr/bin/env python3
"""Synthetic tests for fail-closed distribution-diagnostic reporting."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
from render_precipitation_distribution_table import (  # noqa: E402
    BOUNDARY_FLAGS,
    REQUIRED_WARNING,
    index_locks,
    render_markdown,
    validate_summary,
)
from validate_precipitation_distribution_diagnostic import (  # noqa: E402
    SUMMARY_STATUS,
)
from evaluate_precipitation_distribution_diagnostic import (  # noqa: E402
    DIAGNOSTIC_CONTRACT_ID,
    load_contract,
)


MODELS = [
    "temperature_control",
    "seasonal_quantity",
    "quantity_plus_timing_concentration",
    "quantity_plus_occurrence_intensity",
    "quantity_plus_dry_spells",
    "quantity_plus_wet_extremes",
    "quantity_plus_all_distribution",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_lock(path: Path, spec_hash: str, panel_hashes: dict[str, str]) -> None:
    inputs = ""
    for crop, panel_hash in panel_hashes.items():
        inputs += f'''\n[[inputs]]
crop = "{crop}"
panel_path = "ignored/{crop}.parquet"
panel_sha256 = "{panel_hash}"
allocation_audit_path = "ignored/{crop}_audit.json"
allocation_audit_sha256 = "{'a' * 64}"
expected_rows = 10
expected_observed_outcomes = 10
expected_year_start = 2000
expected_year_end = 2001
'''
    path.write_text(
        f'''schema_version = 1
diagnostic_contract_id = "{DIAGNOSTIC_CONTRACT_ID}"
spec_sha256 = "{spec_hash}"
{inputs}
[boundary]
source_artifacts_are_ignored = true
source_basis_fit_authorized = false
diagnostic_only = true
coefficient_export_authorized = false
scc_use_authorized = false
''',
        encoding="utf-8",
    )


def comparison(holdout: str, offset: float) -> dict[str, object]:
    temperature = 0.80 + offset
    seasonal = 0.90 + offset
    values = {
        "temperature_control": temperature,
        "seasonal_quantity": seasonal,
        # The best extension is still worse than seasonal quantity.  The
        # renderer must report the adverse increment rather than hide it.
        "quantity_plus_timing_concentration": 0.95 + offset,
        "quantity_plus_occurrence_intensity": 0.98 + offset,
        "quantity_plus_dry_spells": 0.97 + offset,
        "quantity_plus_wet_extremes": 0.96 + offset,
        "quantity_plus_all_distribution": 0.99 + offset,
    }
    ranked = [
        {
            "model": model,
            "rmse": rmse,
            "mae": rmse * 0.8,
            "rmse_improvement_vs_zero": 1.2 - rmse,
            "rmse_improvement_vs_temperature_control": temperature - rmse,
            "rmse_improvement_vs_seasonal_quantity": seasonal - rmse,
        }
        for model, rmse in sorted(values.items(), key=lambda item: item[1])
    ]
    return {
        "holdout": holdout,
        "test_rows": 12,
        "zero_change_rmse": 1.2,
        "temperature_control_rmse": temperature,
        "seasonal_quantity_rmse": seasonal,
        "seasonal_quantity_improvement_vs_temperature_control": temperature - seasonal,
        "best_model_descriptive_only": "temperature_control",
        "best_rmse": temperature,
        "ranked_models": ranked,
    }


def make_summary(
    crop: str,
    spec_hash: str,
    lock_hash: str,
    panel_hash: str,
) -> dict[str, object]:
    return {
        "status": SUMMARY_STATUS,
        "diagnostic_contract_id": DIAGNOSTIC_CONTRACT_ID,
        "spec_sha256": spec_hash,
        "lock_sha256": lock_hash,
        "crop": crop,
        "source_panel_sha256": panel_hash,
        **BOUNDARY_FLAGS,
        "wet_day_threshold_mm": 1.0,
        "stage_fractions": [0.0, 0.3, 0.7, 1.0],
        "models": MODELS,
        "n_level_rows": 10,
        "n_observed_level_rows": 10,
        "n_consecutive_pairs": 5,
        "comparisons": [
            comparison("spatial_block", 0.00),
            comparison("temporal", 0.01),
            comparison("climate_extreme", 0.02),
        ],
        "warning": REQUIRED_WARNING,
    }


def expect_failure(
    summary_path: Path,
    summary: dict[str, object],
    spec_path: Path,
    locks: dict[str, Path],
    message: str,
) -> None:
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    try:
        validate_summary(summary_path, spec_path, locks)
        raise AssertionError("Tampered summary should fail")
    except (AssertionError, ValueError) as error:
        assert message in str(error), str(error)


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    spec_path = root / "diagnostic.toml"
    spec_path.write_bytes(
        (PROJECT / "config" / "precipitation_distribution_diagnostic_v1.toml").read_bytes()
    )
    spec_hash = sha256(spec_path)
    panel_hashes = {"mai": "1" * 64, "soy": "2" * 64}
    lock_path = root / "diagnostic.lock.toml"
    write_lock(lock_path, spec_hash, panel_hashes)
    lock_hash = sha256(lock_path)
    # Confirm the synthetic lock itself satisfies the production contract.
    load_contract(spec_path, lock_path)
    locks = index_locks([lock_path])

    maize_path = root / "maize_summary.json"
    soybean_path = root / "soybean_summary.json"
    maize = make_summary("mai", spec_hash, lock_hash, panel_hashes["mai"])
    soybean = make_summary("soy", spec_hash, lock_hash, panel_hashes["soy"])
    maize_path.write_text(json.dumps(maize), encoding="utf-8")
    soybean_path.write_text(json.dumps(soybean), encoding="utf-8")

    rows = validate_summary(maize_path, spec_path, locks)
    rows += validate_summary(soybean_path, spec_path, locks)
    rendered = render_markdown(rows)
    assert rendered.count("| mai |") == 3
    assert rendered.count("| soy |") == 3
    assert "quantity_plus_timing_concentration" in rendered
    assert "-0.050000" in rendered
    assert "does not establish causality" in rendered
    table_only = rendered.split("\n\n*", maxsplit=1)[0]
    assert "coefficient" not in table_only.lower()

    tampered = json.loads(json.dumps(maize))
    tampered["status"] = "unvalidated"
    expect_failure(maize_path, tampered, spec_path, locks, "validation status")

    tampered = json.loads(json.dumps(maize))
    tampered["causal_interpretation_authorized"] = True
    expect_failure(maize_path, tampered, spec_path, locks, "causal_interpretation_authorized=False")

    tampered = json.loads(json.dumps(maize))
    tampered["coefficients_suppressed"] = False
    expect_failure(maize_path, tampered, spec_path, locks, "coefficients_suppressed=True")

    tampered = json.loads(json.dumps(maize))
    tampered["comparisons"][0]["ranked_models"][0]["coefficients"] = [1.0]
    expect_failure(maize_path, tampered, spec_path, locks, "Forbidden fitted-parameter")

    tampered = json.loads(json.dumps(maize))
    tampered["diagnostic_contract_id"] = "wrong"
    expect_failure(maize_path, tampered, spec_path, locks, "contract mismatch")

    tampered = json.loads(json.dumps(maize))
    tampered["spec_sha256"] = "3" * 64
    expect_failure(maize_path, tampered, spec_path, locks, "specification hash")

    tampered = json.loads(json.dumps(maize))
    tampered["lock_sha256"] = "4" * 64
    expect_failure(maize_path, tampered, spec_path, locks, "No supplied diagnostic lock")

    tampered = json.loads(json.dumps(maize))
    tampered["source_panel_sha256"] = "5" * 64
    expect_failure(maize_path, tampered, spec_path, locks, "source-panel hash")

    tampered = json.loads(json.dumps(maize))
    tampered["comparisons"][0]["ranked_models"][2][
        "rmse_improvement_vs_seasonal_quantity"
    ] = 99.0
    expect_failure(maize_path, tampered, spec_path, locks, "Incremental RMSE")

print("precipitation distribution table reporting tests passed")

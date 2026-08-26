#!/usr/bin/env python3
"""Synthetic contract, leakage, hash-drift, and suppression tests."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
from allocate_irrigation_distribution_basis import basis_feature_names  # noqa: E402
from evaluate_precipitation_distribution_diagnostic import (  # noqa: E402
    assert_coefficients_suppressed,
    load_contract,
    run_diagnostic,
)
from validate_precipitation_distribution_diagnostic import validate_audit  # noqa: E402


def synthetic_panel() -> pd.DataFrame:
    rng = np.random.default_rng(20260826)
    rows: list[dict[str, object]] = []
    cell_levels: dict[int, float] = {}
    for grid in range(120):
        cell_levels[grid] = 1.1 + grid * 0.002
        for year in range(2000, 2008):
            stage_days = np.array([30.0, 40.0, 30.0])
            raw_shares = rng.dirichlet([3.0, 4.0, 3.0])
            total_precip = float(110 + 2 * (year - 2000) + (grid % 11) + rng.normal(0, 8))
            stage_precip = total_precip * raw_shares
            stage_wet = np.array(
                [rng.integers(4, 18), rng.integers(5, 24), rng.integers(4, 18)],
                dtype=float,
            )
            stage_cdd = np.array(
                [rng.uniform(2, 12), rng.uniform(2, 15), rng.uniform(2, 12)],
                dtype=float,
            )
            # Create two distinct within-cell extreme years so that the
            # endpoint purge has both retained and held-out pairs.
            if year == 2003:
                stage_cdd[1] += 10
            stage_rx1 = np.minimum(stage_precip * 0.35, rng.uniform(3, 12, size=3))
            if year == 2007:
                stage_rx1[2] = min(stage_precip[2] * 0.45, stage_rx1[2] + 8)
            stage_rx5 = np.minimum(stage_precip, stage_rx1 + rng.uniform(1, 10, size=3))
            stage_temp = np.array(
                [
                    18 + 0.12 * (year - 2000) + rng.normal(0, 0.8),
                    22 + 0.15 * (year - 2000) + rng.normal(0, 0.8),
                    20 + 0.10 * (year - 2000) + rng.normal(0, 0.8),
                ]
            )
            tmean = float(np.average(stage_temp, weights=stage_days))
            log_precip = float(np.log1p(total_precip))
            hhi = float(np.square(raw_shares).sum())
            centroid = float(raw_shares @ np.array([1 / 6, 1 / 2, 5 / 6]))
            shock = (
                0.035 * (log_precip - np.log1p(110))
                + 0.02 * (centroid - 0.5)
                - 0.003 * (tmean - 20)
                + rng.normal(0, 0.008)
            )
            cell_levels[grid] += shock
            row: dict[str, object] = {
                "harvest_year": year,
                "lat": -55.0 + (grid // 24) * 10.0,
                "lon_360": 2.5 + (grid % 24) * 12.5,
                "crop": "mai",
                "yield_observed": True,
                "yield_t_ha": float(np.exp(cell_levels[grid])),
                "season_days": float(stage_days.sum()),
                "tmean_c": tmean,
                "precip_mm": total_precip,
                "log1p_precip_mm": log_precip,
                "wet_days_n": float(stage_wet.sum()),
                "wet_day_frequency": float(stage_wet.sum() / stage_days.sum()),
                "mean_wet_day_intensity_mm": float(total_precip / stage_wet.sum()),
                "cdd_max_days": float(stage_cdd.max()),
                "cdd_fraction": float(stage_cdd.max() / stage_days.sum()),
                "rx1day_mm": float(stage_rx1.max()),
                "rx5day_mm": float(stage_rx5.max()),
                "tmean_x_log1p_precip": tmean * log_precip,
                "zero_precipitation_season": 0.0,
                "precipitation_concentration_hhi": hhi,
                "precipitation_timing_centroid": centroid,
                "irrigation": "area_weighted",
                "exposure_allocation": "regime_basis_before_fixed_area_weighting",
                "weight_source_id": "synthetic_fixed_weights",
                "weight_vintage": "fixed_2000",
                "scc_authorized": False,
                "response_basis_contract_id": "gdhy_aggregate_irrigation_distribution_candidate_v1",
                "basis_allocation_order": "regime_basis_before_fixed_area_weighting",
                "wet_day_threshold_mm": 1.0,
                "nonlinear_post_allocation_transform_authorized": False,
                "direct_pattern_candidate_basis_complete": True,
                "production_model_form_frozen": False,
                "fit_authorized": False,
            }
            for index in range(3):
                stage = index + 1
                prefix = f"stage{stage}_"
                stage_log = float(np.log1p(stage_precip[index]))
                row.update(
                    {
                        f"{prefix}stage_days": float(stage_days[index]),
                        f"{prefix}tmean_c": float(stage_temp[index]),
                        f"{prefix}precip_mm": float(stage_precip[index]),
                        f"{prefix}log1p_precip_mm": stage_log,
                        f"{prefix}precip_share": float(raw_shares[index]),
                        f"{prefix}wet_days_n": float(stage_wet[index]),
                        f"{prefix}wet_day_frequency": float(stage_wet[index] / stage_days[index]),
                        f"{prefix}mean_wet_day_intensity_mm": float(
                            stage_precip[index] / stage_wet[index]
                        ),
                        f"{prefix}cdd_max_days": float(stage_cdd[index]),
                        f"{prefix}cdd_fraction": float(stage_cdd[index] / stage_days[index]),
                        f"{prefix}rx1day_mm": float(stage_rx1[index]),
                        f"{prefix}rx5day_mm": float(stage_rx5[index]),
                        f"{prefix}tmean_x_log1p_precip": float(stage_temp[index] * stage_log),
                    }
                )
            rows.append(row)
    return pd.DataFrame(rows)


def source_audit(panel: pd.DataFrame) -> dict[str, object]:
    features = basis_feature_names(3)
    return {
        "response_basis_contract_id": "gdhy_aggregate_irrigation_distribution_candidate_v1",
        "basis_allocation_order": "regime_basis_before_fixed_area_weighting",
        "basis_features": features,
        "basis_feature_count": len(features),
        "output_rows": len(panel),
        "observed_outcomes": int(panel["yield_observed"].sum()),
        "stage_count": 3,
        "wet_day_threshold_mm": 1.0,
        "fit_authorized": False,
        "scc_authorized": False,
    }


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_lock(
    path: Path,
    spec_hash: str,
    panel_path: Path,
    panel_hash: str,
    audit_path: Path,
    audit_hash: str,
) -> None:
    path.write_text(
        f'''schema_version = 1
diagnostic_contract_id = "gdhy_precipitation_distribution_predictive_diagnostic_v1"
spec_sha256 = "{spec_hash}"

[[inputs]]
crop = "mai"
panel_path = {json.dumps(str(panel_path))}
panel_sha256 = "{panel_hash}"
allocation_audit_path = {json.dumps(str(audit_path))}
allocation_audit_sha256 = "{audit_hash}"
expected_rows = 960
expected_observed_outcomes = 960
expected_year_start = 2000
expected_year_end = 2007

[boundary]
source_artifacts_are_ignored = true
source_basis_fit_authorized = false
diagnostic_only = true
coefficient_export_authorized = false
scc_use_authorized = false
''',
        encoding="utf-8",
    )


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    spec_path = root / "diagnostic.toml"
    spec_path.write_bytes((PROJECT / "config" / "precipitation_distribution_diagnostic_v1.toml").read_bytes())
    panel_path = root / "panel.parquet"
    audit_path = root / "allocation.json"
    lock_path = root / "lock.toml"
    panel = synthetic_panel()
    panel.to_parquet(panel_path, index=False)
    audit_path.write_text(json.dumps(source_audit(panel)), encoding="utf-8")
    write_lock(
        lock_path,
        hash_file(spec_path),
        panel_path,
        hash_file(panel_path),
        audit_path,
        hash_file(audit_path),
    )

    result = run_diagnostic("mai", spec_path, lock_path, root)
    assert result["source_basis_fit_authorized"] is False
    assert result["coefficients_suppressed"] is True
    assert result["scc_use_authorized"] is False
    assert result["n_consecutive_pairs"] == 840
    assert len(result["results"]) == 7 * 3
    assert all(
        row.get("endpoint_overlap_count", 0) == 0
        for row in result["results"]
        if row["holdout"] != "spatial_block"
    )
    assert_coefficients_suppressed(result)
    spec, lock, models, spec_hash, lock_hash = load_contract(spec_path, lock_path)
    summary = validate_audit(
        result,
        spec,
        lock,
        models,
        spec_hash,
        lock_hash,
        root,
        verify_source_files=True,
        recomputed_audit=run_diagnostic("mai", spec_path, lock_path, root),
    )
    assert summary["coefficients_suppressed"] is True
    assert len(summary["comparisons"]) == 3

    leaked = json.loads(json.dumps(result))
    leaked["results"][0]["coefficients"] = [1.0]
    try:
        validate_audit(
            leaked,
            spec,
            lock,
            models,
            spec_hash,
            lock_hash,
            root,
            verify_source_files=True,
            recomputed_audit=result,
        )
        raise AssertionError("Coefficient-bearing diagnostics must fail")
    except AssertionError as error:
        assert "Forbidden fitted-parameter" in str(error)

    abbreviated_leak = json.loads(json.dumps(result))
    abbreviated_leak["results"][0]["coef"] = [1.0]
    try:
        validate_audit(
            abbreviated_leak,
            spec,
            lock,
            models,
            spec_hash,
            lock_hash,
            root,
            verify_source_files=True,
            recomputed_audit=result,
        )
        raise AssertionError("Abbreviated coefficient fields must fail")
    except AssertionError as error:
        assert "Forbidden fitted-parameter" in str(error)

    fabricated_metric = json.loads(json.dumps(result))
    row = fabricated_metric["results"][0]
    row["rmse"] = 0.123
    row["rmse_improvement_vs_zero"] = row["zero_change_rmse"] - row["rmse"]
    try:
        validate_audit(
            fabricated_metric,
            spec,
            lock,
            models,
            spec_hash,
            lock_hash,
            root,
            verify_source_files=True,
            recomputed_audit=result,
        )
        raise AssertionError("Internally consistent fabricated metrics must fail")
    except ValueError as error:
        assert "differs from recomputation" in str(error)

    numeric_false = panel.copy()
    numeric_false["scc_authorized"] = 0
    numeric_false.to_parquet(panel_path, index=False)
    write_lock(
        lock_path,
        hash_file(spec_path),
        panel_path,
        hash_file(panel_path),
        audit_path,
        hash_file(audit_path),
    )
    try:
        run_diagnostic("mai", spec_path, lock_path, root)
        raise AssertionError("Numeric zero must not satisfy an exact false authorization gate")
    except ValueError as error:
        assert "scc_authorized=False" in str(error)

    panel.to_parquet(panel_path, index=False)
    write_lock(
        lock_path,
        hash_file(spec_path),
        panel_path,
        hash_file(panel_path),
        audit_path,
        hash_file(audit_path),
    )

    spec_path.write_bytes(spec_path.read_bytes() + b"\n")
    try:
        run_diagnostic("mai", spec_path, lock_path, root)
        raise AssertionError("Specification-hash drift must fail")
    except ValueError as error:
        assert "hash differs" in str(error)
    spec_path.write_bytes((PROJECT / "config" / "precipitation_distribution_diagnostic_v1.toml").read_bytes())

    drifted = panel.copy()
    drifted["wet_day_threshold_mm"] = 2.0
    drifted.to_parquet(panel_path, index=False)
    write_lock(
        lock_path,
        hash_file(spec_path),
        panel_path,
        hash_file(panel_path),
        audit_path,
        hash_file(audit_path),
    )
    try:
        run_diagnostic("mai", spec_path, lock_path, root)
        raise AssertionError("Wet-day threshold drift must fail")
    except ValueError as error:
        assert "wet-day threshold drift" in str(error).lower()

    drifted["wet_day_threshold_mm"] = 1.0
    drifted["response_basis_contract_id"] = "wrong_contract"
    drifted.to_parquet(panel_path, index=False)
    write_lock(
        lock_path,
        hash_file(spec_path),
        panel_path,
        hash_file(panel_path),
        audit_path,
        hash_file(audit_path),
    )
    try:
        run_diagnostic("mai", spec_path, lock_path, root)
        raise AssertionError("Source-contract drift must fail")
    except ValueError as error:
        assert "invalid response_basis_contract_id" in str(error)

print("precipitation-distribution diagnostic tests passed")

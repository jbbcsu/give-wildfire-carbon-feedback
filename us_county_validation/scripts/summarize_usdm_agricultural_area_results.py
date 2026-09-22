#!/usr/bin/env python3
"""Assemble outcome-blind spatial-basis comparisons for the USDM benchmark."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


TERMS = [f"d{level}_weeks" for level in range(5)]
PUBLISHED_MEANS = dict(zip(TERMS, [8.47, 5.66, 3.87, 2.26, 0.80], strict=True))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def exposure_summary(path: Path) -> dict[str, object]:
    frame = pd.read_parquet(path, columns=[
        "county_geoid", "outcome_crop", "harvest_year", "source_area_basis", *TERMS,
    ])
    basis = set(map(str, frame.source_area_basis.unique()))
    if len(basis) != 1:
        raise ValueError(f"multiple source bases in {path}")
    keys = ["county_geoid", "harvest_year"]
    for _, group in frame.groupby(keys, observed=True):
        if len(group[TERMS].drop_duplicates()) != 1:
            raise ValueError(f"crop-duplicated exposure differs within county-year in {path}")
    unique = frame.drop_duplicates(keys)
    means = {term: float(unique[term].mean()) for term in TERMS}
    return {
        "path": str(path),
        "sha256": sha256(path),
        "source_area_basis": next(iter(basis)),
        "crop_county_year_rows": len(frame),
        "unique_county_years": len(unique),
        "counties": int(unique.county_geoid.nunique()),
        "means_equivalent_weeks": means,
        "absolute_difference_from_published_means": {
            term: abs(means[term] - PUBLISHED_MEANS[term]) for term in TERMS
        },
    }


def result_coefficients(path: Path, family: str | None = None) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for model in payload["results"]:
        if family is not None and model.get("family") != family:
            continue
        indexed = {row["term"]: row for row in model["coefficients"]}
        for term in TERMS:
            row = indexed[term]
            rows.append({
                "outcome_crop": model["outcome_crop"],
                "irrigation_class": model["irrigation_class"],
                "family": family or "drought_only",
                "term": term,
                "estimate_log_points_per_equivalent_week": row[
                    "estimate_log_points_per_area_equivalent_week"
                ],
                "exact_percent_change_per_equivalent_week": row[
                    "exact_percent_change_per_week"
                ],
                "standard_error_county_cluster_cr1": row[
                    "standard_error_county_cluster_cr1"
                ],
                "p_value_normal_reference": row["p_value_normal_reference"],
                "rows": model["rows"],
                "counties": model["counties"],
                "states": model["states"],
            })
    expected = 4 * len(TERMS)
    if len(rows) != expected:
        raise ValueError(f"expected {expected} coefficient rows from {path}, got {len(rows)}")
    return {
        "path": str(path), "sha256": sha256(path),
        "joined_rows": payload.get("joined_panel_rows", payload.get("common_panel_rows")),
        "coefficients": rows,
    }


def robustness_summary(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for model in payload["models"]:
        inference = {row["term"]: row for row in model["full_state_cluster_inference"]}
        leaveout = {row["term"]: row for row in model["leaveout_summaries"]}
        for term in TERMS:
            row = inference[term]
            rows.append({
                "outcome_crop": model["outcome_crop"],
                "irrigation_class": model["irrigation_class"],
                "term": term,
                "estimate_log_points_per_equivalent_week": row["estimate"],
                "exact_percent_change_per_equivalent_week": float(100 * np.expm1(row["estimate"])),
                "standard_error_state_cluster_cr1": row["standard_error_state_cluster_cr1"],
                "p_value_state_t_reference": row["p_value_t_reference"],
                "same_nonzero_sign_fraction_leave_one_state_out": leaveout[term][
                    "same_nonzero_sign_fraction"
                ],
                "state_leaveout_fits": leaveout[term]["leaveout_fits"],
            })
    if len(rows) != 4 * len(TERMS):
        raise ValueError(f"unexpected robustness coefficient count in {path}")
    return {"path": str(path), "sha256": sha256(path), "coefficients": rows}


def main() -> None:
    parser = argparse.ArgumentParser()
    for basis in ("county", "cultivated", "broad"):
        parser.add_argument(f"--{basis}-exposure", type=Path, required=True)
        parser.add_argument(f"--{basis}-drought-result", type=Path, required=True)
        parser.add_argument(f"--{basis}-weather-result", type=Path, required=True)
    parser.add_argument("--cultivated-robustness", type=Path, required=True)
    parser.add_argument("--broad-robustness", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()

    output = {
        "schema": "usdm_agricultural_area_spatial_basis_comparison_v1",
        "published_table_2": {
            "observations": 40040,
            "means_equivalent_weeks": PUBLISHED_MEANS,
            "source": "Kuwayama et al. (2019), Table 2, DOI 10.1093/ajae/aay037",
        },
        "bases": {},
        "selection_rule": "report county, cultivated, and broad bases together; do not choose a mask by coefficient sign, significance, or proximity to published means",
        "causal_claim_authorized": False,
        "damage_claim_authorized": False,
        "global_transfer_authorized": False,
        "scc_claim_authorized": False,
    }
    for basis in ("county", "cultivated", "broad"):
        output["bases"][basis] = {
            "exposure": exposure_summary(getattr(arguments, f"{basis}_exposure")),
            "drought_only": result_coefficients(
                getattr(arguments, f"{basis}_drought_result")
            ),
            "drought_plus_weather": result_coefficients(
                getattr(arguments, f"{basis}_weather_result"), "drought_plus_weather"
            ),
        }
    common_frames = {}
    common_keys = None
    for basis in ("county", "cultivated", "broad"):
        path = getattr(arguments, f"{basis}_exposure")
        frame = pd.read_parquet(path, columns=["county_geoid", "harvest_year", *TERMS])
        frame = frame.drop_duplicates(["county_geoid", "harvest_year"])
        common_frames[basis] = frame
        keys = frame[["county_geoid", "harvest_year"]]
        common_keys = keys if common_keys is None else common_keys.merge(
            keys, on=["county_geoid", "harvest_year"], how="inner", validate="one_to_one"
        )
    output["common_support_exposure_comparison"] = {
        "unique_county_years": len(common_keys),
        "counties": int(common_keys.county_geoid.nunique()),
        "means_equivalent_weeks": {
            basis: {
                term: float(common_keys.merge(
                    frame, on=["county_geoid", "harvest_year"], validate="one_to_one"
                )[term].mean())
                for term in TERMS
            }
            for basis, frame in common_frames.items()
        },
        "interpretation": "holds county-year support fixed; full-support mean differences also reflect source coverage",
    }
    output["bases"]["cultivated"]["state_robustness"] = robustness_summary(
        arguments.cultivated_robustness
    )
    output["bases"]["broad"]["state_robustness"] = robustness_summary(
        arguments.broad_robustness
    )
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote spatial-basis comparison to {arguments.out}")


if __name__ == "__main__":
    main()

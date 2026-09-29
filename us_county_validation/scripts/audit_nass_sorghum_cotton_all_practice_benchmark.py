#!/usr/bin/env python3
"""Audit selection and outcome coherence against all-practice NASS yields."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "US_SORGHUM_COTTON_ALL_PRACTICE_BENCHMARK_PROTOCOL_20260928.md"
KEYS = ["crop", "harvest_year", "county_geoid"]
EXPECTED_UNITS = {"sorghum_grain": "BU / ACRE", "cotton_upland": "LB / ACRE"}


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def parse_value(value: object) -> float:
    text = str(value).strip().replace(",", "")
    if not re.fullmatch(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", text):
        return float("nan")
    number = float(text)
    return number if np.isfinite(number) and number > 0 else float("nan")


def quantiles(values: np.ndarray) -> dict[str, float]:
    if len(values) == 0:
        return {name: 0.0 for name in ("q50", "q90", "q95", "q99", "maximum")}
    return {
        "q50": float(np.quantile(values, 0.50)),
        "q90": float(np.quantile(values, 0.90)),
        "q95": float(np.quantile(values, 0.95)),
        "q99": float(np.quantile(values, 0.99)),
        "maximum": float(np.max(values)),
    }


def selection_classification(coverage: float) -> str:
    if coverage >= 0.50:
        return "broad"
    if coverage >= 0.20:
        return "selected"
    return "highly_selected"


def support_rows(
    all_crop: pd.DataFrame, direct_crop: pd.DataFrame, dimension: str,
) -> list[dict[str, Any]]:
    if dimension == "harvest_year":
        values = list(range(1981, 2019))
    else:
        values = sorted(set(all_crop[dimension].astype(str)) | set(direct_crop[dimension].astype(str)))
    rows = []
    all_keys = all_crop[KEYS].drop_duplicates()
    direct_keys = direct_crop[KEYS].drop_duplicates()
    matched_keys = direct_keys.merge(all_keys, on=KEYS, how="inner", validate="one_to_one")
    for value in values:
        if dimension == "harvest_year":
            universe_n = int(all_crop.harvest_year.eq(value).sum())
            direct_n = int(direct_crop.harvest_year.eq(value).sum())
            matched_n = int(matched_keys.harvest_year.eq(value).sum())
        else:
            universe_n = int(all_crop.state_alpha.astype(str).eq(value).sum())
            direct_n = int(direct_crop.state_alpha.astype(str).eq(value).sum())
            matched_n = int(
                matched_keys.merge(
                    direct_crop[KEYS + ["state_alpha"]].drop_duplicates(),
                    on=KEYS, how="left", validate="one_to_one",
                ).state_alpha.astype(str).eq(value).sum()
            )
        rows.append({
            dimension: value,
            "all_practice_positive_county_years": universe_n,
            "direct_practice_paired_county_years": direct_n,
            "matched_county_years": matched_n,
            "paired_share_of_all_practice": (
                None if universe_n == 0 else direct_n / universe_n
            ),
            "benchmark_match_share_of_direct_pairs": (
                None if direct_n == 0 else matched_n / direct_n
            ),
        })
    return rows


def crop_summary(all_crop: pd.DataFrame, direct_crop: pd.DataFrame) -> dict[str, Any]:
    crop = str(direct_crop.crop.iloc[0])
    expected_unit = EXPECTED_UNITS[crop]
    if set(all_crop.yield_unit) != {expected_unit} or set(direct_crop.yield_unit) != {expected_unit}:
        raise ValueError(f"{crop}: unit mismatch")
    wide = direct_crop.pivot(
        index=KEYS + ["state_alpha"], columns="practice", values="yield_value",
    ).reset_index()
    if set(wide.columns) < {"irrigated", "non_irrigated"} or len(wide) * 2 != len(direct_crop):
        raise ValueError(f"{crop}: direct-practice pivot differs")
    benchmark = all_crop.rename(columns={"yield_value": "all_practice_yield"})
    matched = wide.merge(
        benchmark[KEYS + ["yield_unit", "all_practice_yield"]],
        on=KEYS, how="inner", validate="one_to_one",
    )
    direct_count = len(wide)
    all_count = len(all_crop)
    matched_count = len(matched)
    match_fraction = matched_count / direct_count
    universe_coverage = matched_count / all_count

    irrigated = matched.irrigated.to_numpy(dtype=float)
    non_irrigated = matched.non_irrigated.to_numpy(dtype=float)
    aggregate = matched.all_practice_yield.to_numpy(dtype=float)
    lower = np.minimum(irrigated, non_irrigated)
    upper = np.maximum(irrigated, non_irrigated)
    below = aggregate < lower
    above = aggregate > upper
    equal_both = (aggregate == irrigated) & (aggregate == non_irrigated)
    equal_irrigated = (aggregate == irrigated) & ~equal_both
    equal_non_irrigated = (aggregate == non_irrigated) & ~equal_both
    strictly_between = (aggregate > lower) & (aggregate < upper)
    exact_within = ~(below | above)
    tolerance = np.maximum(0.5, 0.001 * aggregate)
    tolerant_within = (aggregate >= lower - tolerance) & (aggregate <= upper + tolerance)
    outside_distance = np.maximum.reduce((lower - aggregate, aggregate - upper, np.zeros(len(matched))))

    annual = support_rows(all_crop, wide, "harvest_year")
    state = support_rows(all_crop, wide, "state_alpha")
    all_states = sorted(map(str, all_crop.state_alpha.unique()))
    direct_states = sorted(map(str, wide.state_alpha.unique()))
    return {
        "crop": crop,
        "unit": expected_unit,
        "all_practice_universe": {
            "positive_coded_county_years": all_count,
            "counties": int(all_crop.county_geoid.nunique()),
            "states": int(all_crop.state_alpha.nunique()),
            "years_with_positive_rows": int(all_crop.harvest_year.nunique()),
        },
        "direct_practice_sample": {
            "paired_county_years": direct_count,
            "counties": int(wide.county_geoid.nunique()),
            "states": int(wide.state_alpha.nunique()),
        },
        "benchmark_overlap": {
            "matched_county_years": matched_count,
            "match_fraction_of_direct_pairs": match_fraction,
            "paired_share_of_all_practice_universe": universe_coverage,
            "selection_classification": selection_classification(universe_coverage),
            "source_coherence_support_gate_passed": match_fraction >= 0.90,
        },
        "state_support": {
            "all_practice_states": all_states,
            "direct_practice_states": direct_states,
            "all_practice_states_absent_from_direct_sample": sorted(set(all_states) - set(direct_states)),
        },
        "yield_interval_coherence": {
            "matched_county_years": matched_count,
            "below_exact_interval": int(below.sum()),
            "equal_both_practices": int(equal_both.sum()),
            "equal_irrigated_only": int(equal_irrigated.sum()),
            "equal_non_irrigated_only": int(equal_non_irrigated.sum()),
            "strictly_between": int(strictly_between.sum()),
            "above_exact_interval": int(above.sum()),
            "exact_interval_share": float(exact_within.mean()),
            "rounding_tolerant_interval_share": float(tolerant_within.mean()),
            "rounding_tolerant_bracket_gate_passed": bool(tolerant_within.mean() >= 0.95),
            "outside_exact_interval_distance_units": quantiles(outside_distance),
            "positive_distance_violation_count": int((outside_distance > 0).sum()),
        },
        "annual_support": annual,
        "state_support_detail": state,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquisition", type=Path, required=True)
    parser.add_argument("--paired-panel", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to((ROOT / "data/provenance").resolve()):
        raise ValueError("fresh provenance output required")
    acquisition = json.loads(args.acquisition.read_text(encoding="utf-8"))
    if (
        acquisition.get("schema") != "nass_sorghum_cotton_all_practice_acquisition_v1"
        or acquisition.get("status") != "acquired_exact_all_practice_benchmark_no_modeling"
        or acquisition.get("record_count") != 76
    ):
        raise ValueError("benchmark acquisition identity differs")
    all_rows = []
    raw_audits = []
    for record in acquisition["records"]:
        path = ROOT / record["raw_path"]
        if digest(path, "sha512") != record["sha512"]:
            raise ValueError("benchmark raw hash differs")
        rows = json.loads(path.read_text(encoding="utf-8")).get("data")
        if not isinstance(rows, list) or len(rows) != record["count"]:
            raise ValueError("benchmark raw count differs")
        coded_positive = 0
        for raw in rows:
            state = str(raw.get("state_ansi", "")).strip()
            county = str(raw.get("county_ansi", "")).strip()
            geography_ok = bool(re.fullmatch(r"\d{2}", state) and re.fullmatch(r"\d{3}", county))
            value = parse_value(raw.get("Value", ""))
            if geography_ok and np.isfinite(value):
                coded_positive += 1
                all_rows.append({
                    "crop": record["crop"], "harvest_year": int(record["year"]),
                    "county_geoid": state + county,
                    "state_alpha": str(raw.get("state_alpha", "")).strip(),
                    "yield_value": value,
                    "yield_unit": str(raw.get("unit_desc", "")).strip(),
                })
        raw_audits.append({
            "crop": record["crop"], "year": int(record["year"]),
            "raw_rows": len(rows), "positive_coded_rows": coded_positive,
        })
    benchmark = pd.DataFrame(all_rows)
    if benchmark.empty or benchmark.duplicated(KEYS).any():
        raise ValueError("benchmark is empty or duplicates crop/county/year keys")
    paired = pd.read_parquet(args.paired_panel)
    required = set(KEYS + ["state_alpha", "practice", "yield_value", "yield_unit"])
    if required - set(paired.columns) or paired.duplicated(KEYS + ["practice"]).any():
        raise ValueError("paired panel schema or uniqueness differs")
    if not paired.groupby(KEYS, observed=True).size().eq(2).all():
        raise ValueError("paired panel does not contain two rows per key")
    if not paired.groupby(KEYS, observed=True).practice.agg(set).map(
        lambda value: value == {"irrigated", "non_irrigated"}
    ).all():
        raise ValueError("paired panel practice labels differ")
    if not np.isfinite(paired.yield_value).all() or not paired.yield_value.gt(0).all():
        raise ValueError("paired yields are not finite positive")

    summaries = []
    for crop in EXPECTED_UNITS:
        all_crop = benchmark.loc[benchmark.crop.eq(crop)].copy()
        direct_long = paired.loc[paired.crop.eq(crop)].copy()
        summaries.append(crop_summary(all_crop, direct_long))
    result = {
        "schema": "nass_sorghum_cotton_all_practice_benchmark_audit_v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": "completed_support_selection_and_outcome_coherence_audit",
        "inputs": {
            "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": digest(PROTOCOL)},
            "acquisition": {"path": str(args.acquisition), "sha256": digest(args.acquisition)},
            "paired_panel": {"path": str(args.paired_panel), "sha256": digest(args.paired_panel)},
            "implementation": {
                "path": str(Path(__file__).resolve().relative_to(ROOT)),
                "sha256": digest(Path(__file__).resolve()),
            },
        },
        "raw_file_audits": raw_audits,
        "crop_summaries": summaries,
        "weather_or_drought_index_read": False,
        "direct_weather_and_pdsi_spei_families_combined": False,
        "coefficients_or_predictions_emitted": False,
        "causal_claim_authorized": False,
        "irrigation_treatment_claim_authorized": False,
        "national_representativeness_claim_authorized": False,
        "future_or_global_transfer_authorized": False,
        "damage_claim_authorized": False,
        "scc_claim_authorized": False,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "crop_decisions": {
            row["crop"]: {
                "selection": row["benchmark_overlap"]["selection_classification"],
                "support_gate": row["benchmark_overlap"]["source_coherence_support_gate_passed"],
                "bracket_gate": row["yield_interval_coherence"]["rounding_tolerant_bracket_gate_passed"],
            }
            for row in summaries
        },
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Map validated FAIR temperature pulses through published EPA rain slopes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EPA_DIR = ROOT / "data/interim/epa_annual_country_pattern_benchmark_20260921"
EPA_RESULT = EPA_DIR / "result.json"
EPA_SLOPES = EPA_DIR / "country_model_slopes.csv"
FAIR_PATHS = ROOT / "data/interim/give_fair_temperature_path_smoke/temperature_paths.csv"
FAIR_RECEIPT = ROOT / "data/provenance/give_fair_temperature_path_smoke_20260827.json"
PROTOCOL = ROOT / "EPA_FAIR_ANNUAL_PRECIPITATION_PULSE_PROTOCOL_20260921.md"
EPA_RESULT_SHA = "f444a693120b4040c959f5425a1fc2e641a6150fd4566aaf033ed2b202388c19"
EPA_SLOPES_SHA = "e6bc9a4dbc0af19650f2f243802e0e1974d3599292cf2704aad0e746bf0c0572"
FAIR_PATHS_SHA = "aedf6b66dd296337e1cb6105d2aa56ec94f3e15e5ac92c2abcdf74b6a42b6067"
YEARS = [2021, 2030, 2050, 2100, 2200, 2300]
PULSES = [0.0001, 0.00005, 0.000025]


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def distribution(values: np.ndarray) -> dict[str, float]:
    if values.ndim != 1 or len(values) == 0 or not np.isfinite(values).all():
        raise ValueError("EPA/FAIR precipitation distribution invalid")
    q = np.quantile(values, [0.05, 0.25, 0.5, 0.75, 0.95])
    return {
        "minimum_mm_per_year": float(values.min()),
        "q05_mm_per_year": float(q[0]),
        "q25_mm_per_year": float(q[1]),
        "median_mm_per_year": float(q[2]),
        "q75_mm_per_year": float(q[3]),
        "q95_mm_per_year": float(q[4]),
        "maximum_mm_per_year": float(values.max()),
        "mean_mm_per_year": float(values.mean()),
        "positive_pair_fraction": float(np.mean(values > 0)),
        "negative_pair_fraction": float(np.mean(values < 0)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        raise ValueError("fresh ignored EPA/FAIR output required")
    if sha(EPA_RESULT) != EPA_RESULT_SHA or sha(EPA_SLOPES) != EPA_SLOPES_SHA or sha(FAIR_PATHS) != FAIR_PATHS_SHA:
        raise ValueError("EPA or FAIR parent artifact hash changed")
    epa = json.loads(EPA_RESULT.read_text())
    fair_receipt = json.loads(FAIR_RECEIPT.read_text())
    if (epa["status"] != "epa_annual_country_precipitation_pattern_benchmark_not_damage_or_scc" or
            epa["support"]["finite_country_model_pairs"] != 4703 or
            fair_receipt["result"] != "passed" or fair_receipt["paths_sha256"] != FAIR_PATHS_SHA or
            fair_receipt["zero_pulse_identity"] is not True or fair_receipt["pre_pulse_identity"] is not True):
        raise ValueError("validated EPA or FAIR parent status unavailable")
    slopes = pd.read_csv(EPA_SLOPES)
    if str(slopes["slope_available"].dtype) != "bool":
        raise ValueError("EPA slope-availability flag is no longer Boolean")
    finite = slopes.loc[slopes.slope_available].copy()
    beta = finite["patterns.area"].to_numpy(dtype=float)
    if (len(slopes) != 4784 or len(finite) != 4703 or finite.iso3.nunique() != 184 or
            not np.isfinite(beta).all() or finite.duplicated(["iso3", "source"]).any()):
        raise ValueError("EPA finite slope support changed")
    fair = pd.read_csv(FAIR_PATHS)
    if (len(fair) != 2204 or set(fair.year) != set(range(1750, 2301)) or
            set(fair.pulse_size_gtc) != {0.0, *PULSES} or
            fair.duplicated(["year", "pulse_size_gtc"]).any()):
        raise ValueError("FAIR path support changed")
    if not np.allclose(fair.difference_k,
                       fair.pulse_temperature_c - fair.baseline_temperature_c,
                       rtol=0, atol=1e-15):
        raise ValueError("FAIR temperature difference identity failed")
    if not np.allclose(fair.loc[fair.pulse_size_gtc.eq(0), "difference_k"], 0, rtol=0, atol=0):
        raise ValueError("FAIR zero pulse changed")
    if not np.allclose(fair.loc[fair.year.le(2020), "difference_k"], 0, rtol=0, atol=0):
        raise ValueError("FAIR pre-pulse identity changed")
    baseline = fair.pivot(index="year", columns="pulse_size_gtc", values="baseline_temperature_c")
    if not baseline.nunique(axis=1, dropna=False).eq(1).all():
        raise ValueError("FAIR baseline path differs across pulse cases")

    selected = []
    for pulse in PULSES:
        for year in YEARS:
            row = fair.loc[fair.pulse_size_gtc.eq(pulse) & fair.year.eq(year)]
            if len(row) != 1:
                raise ValueError("FAIR selected pulse/year missing")
            delta_t = float(row.difference_k.iloc[0])
            values = beta * delta_t
            country_medians = (finite.assign(delta_precip=values)
                               .groupby("iso3").delta_precip.median())
            selected.append({
                "year": year,
                "pulse_size_gtc": pulse,
                "temperature_difference_k": delta_t,
                **distribution(values),
                "positive_country_medians": int(country_medians.gt(0).sum()),
                "negative_country_medians": int(country_medians.lt(0).sum()),
                "zero_country_medians": int(country_medians.eq(0).sum()),
            })

    wide = fair.loc[fair.year.gt(2020) & fair.pulse_size_gtc.isin(PULSES)].pivot(
        index="year", columns="pulse_size_gtc", values="difference_k")
    small, next_small = PULSES[-1], PULSES[-2]
    normalized_small = wide[small].to_numpy(dtype=float) / small
    normalized_next = wide[next_small].to_numpy(dtype=float) / next_small
    temperature_difference = np.abs(normalized_small - normalized_next)
    temperature_scale = np.maximum.reduce([
        np.abs(normalized_small), np.abs(normalized_next), np.full(len(wide), 1e-15)])
    temperature_relative = temperature_difference / temperature_scale
    max_abs_beta = float(np.max(np.abs(beta)))
    result = {
        "status": "published_epa_fair_annual_precipitation_pulse_benchmark_not_damage_or_scc",
        "formula": "country_model_slope_mm_per_year_per_K_times_pulse_minus_baseline_temperature_K",
        "epa_result_sha256": sha(EPA_RESULT),
        "epa_slope_table_sha256": sha(EPA_SLOPES),
        "fair_temperature_paths_sha256": sha(FAIR_PATHS),
        "fair_validation_receipt_sha256": sha(FAIR_RECEIPT),
        "protocol_sha256": sha(PROTOCOL),
        "code_sha256": sha(Path(__file__)),
        "finite_country_model_pairs": len(beta),
        "countries": int(finite.iso3.nunique()),
        "selected_year_summaries": selected,
        "convergence": {
            "years": [int(wide.index.min()), int(wide.index.max())],
            "smallest_pulse_gtc": small,
            "next_smallest_pulse_gtc": next_small,
            "maximum_absolute_normalized_temperature_disagreement_k_per_gtc": float(temperature_difference.max()),
            "maximum_relative_normalized_temperature_disagreement": float(temperature_relative.max()),
            "maximum_absolute_normalized_precipitation_disagreement_mm_per_year_per_gtc":
                float(temperature_difference.max() * max_abs_beta),
            "maximum_relative_normalized_precipitation_disagreement": float(temperature_relative.max()),
        },
        "zero_pulse_identity": True,
        "pre_pulse_identity_through_2020": True,
        "daily_timing_or_extremes_represented": False,
        "crop_response_estimated": False,
        "economic_damage_or_scc_estimated": False,
    }
    out.mkdir(parents=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "selected_rows": len(selected),
                      "max_relative_convergence_error": float(temperature_relative.max())}))


if __name__ == "__main__":
    main()

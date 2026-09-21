#!/usr/bin/env python3
"""Build the registered EPA annual country precipitation-slope benchmark."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data/raw/research_inputs/usepa_pattern_scaling_dac5503"
SOURCE = SOURCE_DIR / "pattern_scaling_precipitation_by_country_full_sample.csv"
UPSTREAM_CODE = SOURCE_DIR / "make_patterns_for_give.R"
PROTOCOL = ROOT / "EPA_ANNUAL_COUNTRY_PATTERN_PROTOCOL_20260921.md"
SOURCE_SHA = "131fa989f43f3d9354da23eecf1cb647dc5c24399671e78fab93230d8902a013"
CODE_SHA = "a4651abe5a743d7aa1fd2a22050ba3a3c267601524da4b9243a1a58967231241"
SCENARIOS = ["ssp1", "ssp2", "ssp3", "ssp4", "ssp5"]
OVERLAP = ["MPI-ESM1-2-HR", "MRI-ESM2-0", "UKESM1-0-LL"]
KEY = ["iso3", "source", "scenario"]


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_source() -> pd.DataFrame:
    if sha(SOURCE) != SOURCE_SHA or sha(UPSTREAM_CODE) != CODE_SHA:
        raise ValueError("EPA source or reviewed aggregation code hash changed")
    frame = pd.read_csv(SOURCE)
    required = {"name", "iso3", "continent", "patterns.area", "scenario", "source"}
    if not required <= set(frame.columns) or len(frame) != 23920:
        raise ValueError("EPA country-output schema or row count changed")
    values = frame["patterns.area"].to_numpy(dtype=float)
    if (frame.duplicated(KEY).any() or frame.iso3.nunique() != 184 or
            frame.source.nunique() != 26 or sorted(frame.scenario.unique()) != SCENARIOS or
            frame.groupby(["iso3", "source"]).ngroups != 4784 or
            np.isinf(values).any() or int(np.isnan(values).sum()) != 405):
        raise ValueError("EPA country/model/scenario support invalid")
    grouped = frame.groupby(["iso3", "source"])["patterns.area"]
    finite_counts = grouped.count()
    if (not finite_counts.isin([0, 5]).all() or int(finite_counts.eq(0).sum()) != 81):
        raise ValueError("EPA missingness differs across socioeconomic labels")
    spread = grouped.agg(lambda x: x.max() - x.min())
    if not np.allclose(spread.loc[finite_counts.eq(5)].to_numpy(dtype=float),
                       0.0, rtol=0.0, atol=0.0):
        raise ValueError("EPA area-weighted climate slope changes across socioeconomic labels")
    representative = frame.loc[frame.scenario.eq("ssp2")].copy()
    representative["slope_available"] = representative["patterns.area"].notna()
    if len(representative) != 4784 or int(representative.slope_available.sum()) != 4703:
        raise ValueError("EPA representative country/model table incomplete")
    return representative


def summarize_country(group: pd.DataFrame) -> pd.Series:
    all_values = group["patterns.area"].to_numpy(dtype=float)
    values = all_values[np.isfinite(all_values)]
    if len(values) == 0:
        raise ValueError("EPA country has no available model slope")
    quantiles = np.quantile(values, [0.05, 0.25, 0.5, 0.75, 0.95])
    return pd.Series({
        "name": group["name"].iloc[0],
        "continent": group["continent"].iloc[0],
        "available_models": len(values),
        "missing_models": len(all_values) - len(values),
        "minimum_mm_per_year_per_k": float(values.min()),
        "q05_mm_per_year_per_k": float(quantiles[0]),
        "q25_mm_per_year_per_k": float(quantiles[1]),
        "median_mm_per_year_per_k": float(quantiles[2]),
        "q75_mm_per_year_per_k": float(quantiles[3]),
        "q95_mm_per_year_per_k": float(quantiles[4]),
        "maximum_mm_per_year_per_k": float(values.max()),
        "mean_mm_per_year_per_k": float(values.mean()),
        "sd_mm_per_year_per_k": float(values.std(ddof=1)),
        "positive_model_fraction": float(np.mean(values > 0)),
        "negative_model_fraction": float(np.mean(values < 0)),
    })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        raise ValueError("fresh ignored EPA benchmark output required")
    representative = load_source().sort_values(["iso3", "source"]).reset_index(drop=True)
    country = (representative.groupby("iso3", sort=True, group_keys=False)
               .apply(summarize_country, include_groups=False).reset_index())
    if len(country) != 184 or int(country.available_models.sum()) != 4703:
        raise ValueError("EPA country summary support invalid")
    aggregate = {
        "countries": len(country),
        "median_positive": int(country.median_mm_per_year_per_k.gt(0).sum()),
        "median_negative": int(country.median_mm_per_year_per_k.lt(0).sum()),
        "median_zero": int(country.median_mm_per_year_per_k.eq(0).sum()),
        "unanimous_positive": int(country.positive_model_fraction.eq(1).sum()),
        "unanimous_negative": int(country.negative_model_fraction.eq(1).sum()),
        "at_least_80pct_positive": int(country.positive_model_fraction.ge(0.8).sum()),
        "at_least_80pct_negative": int(country.negative_model_fraction.ge(0.8).sum()),
        "q05_positive": int(country.q05_mm_per_year_per_k.gt(0).sum()),
        "q95_negative": int(country.q95_mm_per_year_per_k.lt(0).sum()),
    }
    overlap = {}
    for model in OVERLAP:
        all_values = representative.loc[representative.source.eq(model), "patterns.area"].to_numpy(float)
        values = all_values[np.isfinite(all_values)]
        if len(all_values) != 184 or len(values) == 0:
            raise ValueError(f"overlapping EPA model support invalid: {model}")
        overlap[model] = {
            "countries": len(values),
            "missing_countries": len(all_values) - len(values),
            "q05_mm_per_year_per_k": float(np.quantile(values, 0.05)),
            "median_mm_per_year_per_k": float(np.median(values)),
            "q95_mm_per_year_per_k": float(np.quantile(values, 0.95)),
            "positive_country_fraction": float(np.mean(values > 0)),
            "negative_country_fraction": float(np.mean(values < 0)),
        }
    ranked = country.sort_values(["median_mm_per_year_per_k", "iso3"])
    rank_fields = ["iso3", "name", "median_mm_per_year_per_k",
                   "q05_mm_per_year_per_k", "q95_mm_per_year_per_k"]
    result = {
        "status": "epa_annual_country_precipitation_pattern_benchmark_not_damage_or_scc",
        "units": "mm_per_year_per_K_GMST",
        "source_commit": "dac5503549d5158e0257894012293acff45c0cb4",
        "source_sha256": sha(SOURCE),
        "upstream_aggregation_code_sha256": sha(UPSTREAM_CODE),
        "protocol_sha256": sha(PROTOCOL),
        "code_sha256": sha(Path(__file__)),
        "support": {"raw_rows": 23920, "scenarios": SCENARIOS,
                    "scenario_deduplicated_rows": len(representative),
                    "finite_country_model_pairs": int(representative.slope_available.sum()),
                    "missing_country_model_pairs": int((~representative.slope_available).sum()),
                    "countries": 184, "models": 26,
                    "minimum_available_models_per_country": int(country.available_models.min()),
                    "maximum_available_models_per_country": int(country.available_models.max())},
        "country_count_summary": aggregate,
        "overlapping_model_country_count_summaries": overlap,
        "five_smallest_country_medians": ranked.head(5)[rank_fields].to_dict("records"),
        "five_largest_country_medians": ranked.tail(5)[rank_fields].to_dict("records"),
        "weighting_warning": "country counts and within-country area-weighted slopes; not global land/crop/value weighting",
        "daily_timing_or_extremes_represented": False,
        "crop_response_estimated": False,
        "economic_damage_or_scc_estimated": False,
    }
    out.mkdir(parents=True)
    representative.to_csv(out / "country_model_slopes.csv", index=False, float_format="%.12g")
    country.to_csv(out / "country_summary.csv", index=False, float_format="%.12g")
    result["country_model_slopes_sha256"] = sha(out / "country_model_slopes.csv")
    result["country_summary_sha256"] = sha(out / "country_summary.csv")
    (out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], **aggregate}))


if __name__ == "__main__":
    main()

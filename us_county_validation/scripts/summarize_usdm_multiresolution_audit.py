#!/usr/bin/env python3
"""Apply the frozen USDM multi-resolution advancement thresholds."""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd


CATEGORIES = ("none", "d0", "d1", "d2", "d3", "d4")
DROUGHT_COLUMNS = tuple(f"weeks_{name}" for name in CATEGORIES[1:])


def sha512_file(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def summary(values: np.ndarray) -> dict[str, float]:
    return {
        "count": int(len(values)),
        "median": float(np.median(values)),
        "p90": float(np.quantile(values, 0.9)),
        "maximum": float(np.max(values)),
        "mean": float(np.mean(values)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--native-run-audit", type=Path, required=True)
    parser.add_argument("--fine-grid-audit", type=Path, required=True)
    parser.add_argument("--fine-grid-resource", type=Path, required=True)
    parser.add_argument("--coarse-exposure", type=Path, required=True)
    parser.add_argument("--fine-exposure", type=Path, required=True)
    parser.add_argument("--fine-exposure-resource", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()
    contract = tomllib.loads(arguments.config.read_text(encoding="utf-8"))
    thresholds = contract["thresholds"]
    selection = json.loads(arguments.selection.read_text(encoding="utf-8"))
    native_run = json.loads(arguments.native_run_audit.read_text(encoding="utf-8"))
    if int(native_run["sentinel_weeks"]) != 24 or len(native_run["runs"]) != 24:
        raise ValueError("native run does not contain the frozen 24 county-weeks")
    expected_pairs = {
        (str(county["county_geoid"]), str(week["map_date"]))
        for county in selection["sentinels"] for week in county["selected_weeks"]
    }
    if len(expected_pairs) != 24:
        raise ValueError("selection does not contain 24 unique county-weeks")
    fine_grid_audit = json.loads(arguments.fine_grid_audit.read_text(encoding="utf-8"))
    expected_pixels = {
        (str(row["county_geoid"]), str(row["mask_id"])): int(row["agricultural_pixels"])
        for row in fine_grid_audit["counties"]
    }
    weekly_rows = []
    seen_pairs = set()
    selection_sha512 = sha512_file(arguments.selection)
    for receipt in native_run["runs"]:
        path = Path(receipt["result"])
        if sha512_file(path) != receipt["result_sha512"]:
            raise ValueError(f"native sentinel identity differs for {path.name}")
        result = json.loads(path.read_text(encoding="utf-8"))
        if result["sources"]["selection_sha512"] != selection_sha512:
            raise ValueError("native result selection identity differs")
        pair = (str(result["county_geoid"]), str(result["map_date"]))
        if pair not in expected_pairs or pair in seen_pairs:
            raise ValueError("native result support differs from selection")
        seen_pairs.add(pair)
        for mask, row in result["masks"].items():
            native = np.asarray(row["native_shares"], dtype=np.float64)
            coarse = np.asarray(row["coarse_3960m_shares"], dtype=np.float64)
            fine = np.asarray(row["fine_990m_shares"], dtype=np.float64)
            if not all(np.isclose(values.sum(), 1, rtol=0, atol=1e-10) for values in (native, coarse, fine)):
                raise ValueError("one or more weekly share vectors do not sum to one")
            if int(row["native_total_pixels"]) != expected_pixels[(pair[0], mask)]:
                raise ValueError("native pixel total differs from independently built fine-grid audit")
            coarse_tvd = float(0.5 * np.abs(coarse - native).sum())
            fine_tvd = float(0.5 * np.abs(fine - native).sum())
            if not np.isclose(coarse_tvd, float(row["coarse_native_tvd"]), rtol=0, atol=1e-14):
                raise ValueError("reported coarse TVD differs from shares")
            if not np.isclose(fine_tvd, float(row["fine_native_tvd"]), rtol=0, atol=1e-14):
                raise ValueError("reported fine TVD differs from shares")
            weekly_rows.append({
                "county_geoid": pair[0], "map_date": pair[1], "mask_id": mask,
                "native_total_pixels": int(row["native_total_pixels"]),
                "coarse_native_tvd": coarse_tvd, "fine_native_tvd": fine_tvd,
            })
    if seen_pairs != expected_pairs or len(weekly_rows) != 48:
        raise ValueError("native weekly comparison support is incomplete")
    coarse_tvd = np.asarray([row["coarse_native_tvd"] for row in weekly_rows])
    fine_tvd = np.asarray([row["fine_native_tvd"] for row in weekly_rows])
    coarse_weekly = summary(coarse_tvd)
    fine_weekly = summary(fine_tvd)

    sentinel_counties = sorted({pair[0] for pair in expected_pairs})
    coarse = pd.read_parquet(arguments.coarse_exposure)
    fine = pd.read_parquet(arguments.fine_exposure)
    coarse = coarse[coarse.county_geoid.astype(str).str.zfill(5).isin(sentinel_counties)].copy()
    coarse["county_geoid"] = coarse.county_geoid.astype(str).str.zfill(5)
    fine["county_geoid"] = fine.county_geoid.astype(str).str.zfill(5)
    keys = ["county_geoid", "mask_id", "harvest_year"]
    merged = coarse[keys + list(DROUGHT_COLUMNS)].merge(
        fine[keys + list(DROUGHT_COLUMNS)], on=keys, how="outer", suffixes=("_3960m", "_990m"), indicator=True,
    )
    if len(merged) != 8 * 2 * 13 or not merged._merge.eq("both").all():
        raise ValueError("annual coarse/fine support differs from the frozen 8 x 2 x 13 design")
    annual_rows = []
    for row in merged.itertuples(index=False):
        for category in CATEGORIES[1:]:
            coarse_value = float(getattr(row, f"weeks_{category}_3960m"))
            fine_value = float(getattr(row, f"weeks_{category}_990m"))
            annual_rows.append({
                "county_geoid": row.county_geoid, "mask_id": row.mask_id,
                "harvest_year": int(row.harvest_year), "category": category,
                "coarse_weeks": coarse_value, "fine_weeks": fine_value,
                "absolute_difference_weeks": abs(coarse_value - fine_value),
            })
    annual_values = np.asarray([row["absolute_difference_weeks"] for row in annual_rows])
    annual = summary(annual_values)

    gates = {
        "weekly_coarse_native_median": coarse_weekly["median"] <= float(thresholds["weekly_tvd_median_max"]),
        "weekly_coarse_native_p90": coarse_weekly["p90"] <= float(thresholds["weekly_tvd_p90_max"]),
        "weekly_coarse_native_maximum": coarse_weekly["maximum"] <= float(thresholds["weekly_tvd_max"]),
        "annual_coarse_fine_median": annual["median"] <= float(thresholds["annual_absolute_weeks_median_max"]),
        "annual_coarse_fine_p90": annual["p90"] <= float(thresholds["annual_absolute_weeks_p90_max"]),
        "annual_coarse_fine_maximum": annual["maximum"] <= float(thresholds["annual_absolute_weeks_max"]),
        "fine_native_median_noninferiority": fine_weekly["median"] - coarse_weekly["median"] <= float(thresholds["fine_minus_coarse_tvd_median_max"]),
        "fine_native_p90_noninferiority": fine_weekly["p90"] - coarse_weekly["p90"] <= float(thresholds["fine_minus_coarse_tvd_p90_max"]),
        "resource_ceiling": int(native_run["maximum_peak_rss_bytes"]) <= int(contract["resource_ceiling_bytes"]),
    }
    output = {
        "schema": "usdm_multiresolution_sentinel_results_v1",
        "config": str(arguments.config),
        "selection": {"path": str(arguments.selection), "sha512": selection_sha512},
        "weekly_native_reference": {
            "coarse_3960m_tvd": coarse_weekly,
            "fine_990m_tvd": fine_weekly,
            "rows": weekly_rows,
        },
        "annual_3960m_vs_990m": {"absolute_difference_weeks": annual, "rows": annual_rows},
        "gates": gates,
        "passed": all(gates.values()),
        "failed_gates": sorted(key for key, value in gates.items() if not value),
        "resource": {
            "maximum_native_worker_peak_rss_bytes": int(native_run["maximum_peak_rss_bytes"]),
            "fine_grid_peak_rss_bytes": int(json.loads(arguments.fine_grid_resource.read_text())["peak_rss_bytes"]),
            "fine_exposure_peak_rss_bytes": int(json.loads(arguments.fine_exposure_resource.read_text())["peak_rss_bytes"]),
            "ceiling_bytes": int(contract["resource_ceiling_bytes"]),
        },
        "claim_boundary": "spatial measurement sensitivity only; passing or failing does not identify causal yield effects, future drought, global damages, or SCC",
        "causal_claim_authorized": False,
        "damage_claim_authorized": False,
        "global_transfer_authorized": False,
        "scc_claim_authorized": False,
    }
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "passed": output["passed"], "failed_gates": output["failed_gates"],
        "coarse_weekly": coarse_weekly, "fine_weekly": fine_weekly, "annual": annual,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

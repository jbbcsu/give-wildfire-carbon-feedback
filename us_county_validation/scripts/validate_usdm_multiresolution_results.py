#!/usr/bin/env python3
"""Independently recalculate the frozen USDM resolution decision."""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd


CATEGORIES = ("none", "d0", "d1", "d2", "d3", "d4")


def sha512_file(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stats(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "count": int(array.size), "median": float(np.percentile(array, 50)),
        "p90": float(np.percentile(array, 90)), "maximum": float(array.max()),
        "mean": float(array.sum() / array.size),
    }


def assert_stats(actual: dict, expected: dict, label: str) -> None:
    if int(actual["count"]) != int(expected["count"]):
        raise ValueError(f"{label} count differs")
    for key in ("median", "p90", "maximum", "mean"):
        if not np.isclose(float(actual[key]), float(expected[key]), rtol=0, atol=1e-13):
            raise ValueError(f"{label} {key} differs")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--native-run-audit", type=Path, required=True)
    parser.add_argument("--coarse-exposure", type=Path, required=True)
    parser.add_argument("--fine-exposure", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()
    contract = tomllib.loads(arguments.config.read_text(encoding="utf-8"))
    threshold = contract["thresholds"]
    selection = json.loads(arguments.selection.read_text(encoding="utf-8"))
    run = json.loads(arguments.native_run_audit.read_text(encoding="utf-8"))
    reported = json.loads(arguments.result.read_text(encoding="utf-8"))
    expected_pairs = {
        (str(county["county_geoid"]), str(week["map_date"]))
        for county in selection["sentinels"] for week in county["selected_weeks"]
    }
    coarse_tvd, fine_tvd, weekly_identity = [], [], []
    selection_sha512 = sha512_file(arguments.selection)
    for receipt in run["runs"]:
        path = Path(receipt["result"])
        if sha512_file(path) != receipt["result_sha512"]:
            raise ValueError("native result checksum differs")
        value = json.loads(path.read_text(encoding="utf-8"))
        if value["sources"]["selection_sha512"] != selection_sha512:
            raise ValueError("native result selection checksum differs")
        pair = (str(value["county_geoid"]), str(value["map_date"]))
        if pair not in expected_pairs:
            raise ValueError("native result lies outside selection")
        for mask, row in value["masks"].items():
            native = np.asarray(row["native_shares"], dtype=np.float64)
            coarse = np.asarray(row["coarse_3960m_shares"], dtype=np.float64)
            fine = np.asarray(row["fine_990m_shares"], dtype=np.float64)
            coarse_value = float(np.abs(native - coarse).sum() / 2)
            fine_value = float(np.abs(native - fine).sum() / 2)
            coarse_tvd.append(coarse_value)
            fine_tvd.append(fine_value)
            weekly_identity.append((coarse_value, pair[0], pair[1], mask))
    coarse_stats, fine_stats = stats(coarse_tvd), stats(fine_tvd)
    assert_stats(coarse_stats, reported["weekly_native_reference"]["coarse_3960m_tvd"], "coarse weekly")
    assert_stats(fine_stats, reported["weekly_native_reference"]["fine_990m_tvd"], "fine weekly")

    counties = sorted({pair[0] for pair in expected_pairs})
    coarse = pd.read_parquet(arguments.coarse_exposure)
    fine = pd.read_parquet(arguments.fine_exposure)
    coarse["county_geoid"] = coarse.county_geoid.astype(str).str.zfill(5)
    fine["county_geoid"] = fine.county_geoid.astype(str).str.zfill(5)
    coarse = coarse[coarse.county_geoid.isin(counties)]
    keys = ["county_geoid", "mask_id", "harvest_year"]
    columns = [f"weeks_{name}" for name in CATEGORIES[1:]]
    joined = coarse[keys + columns].merge(fine[keys + columns], on=keys, validate="one_to_one", suffixes=("_c", "_f"))
    if len(joined) != 208:
        raise ValueError("annual comparison support differs")
    annual_values, annual_identity = [], []
    for row in joined.itertuples(index=False):
        for category in CATEGORIES[1:]:
            difference = abs(float(getattr(row, f"weeks_{category}_c")) - float(getattr(row, f"weeks_{category}_f")))
            annual_values.append(difference)
            annual_identity.append((difference, row.county_geoid, row.mask_id, int(row.harvest_year), category))
    annual_stats = stats(annual_values)
    assert_stats(annual_stats, reported["annual_3960m_vs_990m"]["absolute_difference_weeks"], "annual")

    gates = {
        "weekly_coarse_native_median": coarse_stats["median"] <= float(threshold["weekly_tvd_median_max"]),
        "weekly_coarse_native_p90": coarse_stats["p90"] <= float(threshold["weekly_tvd_p90_max"]),
        "weekly_coarse_native_maximum": coarse_stats["maximum"] <= float(threshold["weekly_tvd_max"]),
        "annual_coarse_fine_median": annual_stats["median"] <= float(threshold["annual_absolute_weeks_median_max"]),
        "annual_coarse_fine_p90": annual_stats["p90"] <= float(threshold["annual_absolute_weeks_p90_max"]),
        "annual_coarse_fine_maximum": annual_stats["maximum"] <= float(threshold["annual_absolute_weeks_max"]),
        "fine_native_median_noninferiority": fine_stats["median"] - coarse_stats["median"] <= float(threshold["fine_minus_coarse_tvd_median_max"]),
        "fine_native_p90_noninferiority": fine_stats["p90"] - coarse_stats["p90"] <= float(threshold["fine_minus_coarse_tvd_p90_max"]),
        "resource_ceiling": int(run["maximum_peak_rss_bytes"]) <= int(contract["resource_ceiling_bytes"]),
    }
    if gates != reported["gates"] or all(gates.values()) != bool(reported["passed"]):
        raise ValueError("independent gate decision differs from reported result")
    output = {
        "schema": "usdm_multiresolution_independent_validation_v1",
        "status": "passed",
        "result": {"path": str(arguments.result), "sha512": sha512_file(arguments.result)},
        "recalculated_decision": all(gates.values()),
        "failed_gates": sorted(key for key, value in gates.items() if not value),
        "largest_weekly_error": {
            "tvd": max(weekly_identity)[0], "county_geoid": max(weekly_identity)[1],
            "map_date": max(weekly_identity)[2], "mask_id": max(weekly_identity)[3],
        },
        "largest_annual_error": {
            "absolute_difference_weeks": max(annual_identity)[0],
            "county_geoid": max(annual_identity)[1], "mask_id": max(annual_identity)[2],
            "harvest_year": max(annual_identity)[3], "category": max(annual_identity)[4],
        },
        "checks": {"weekly_mask_rows": len(coarse_tvd), "annual_category_rows": len(annual_values)},
        "claim_boundary": "independent arithmetic validation of a spatial approximation decision only; not causal, damage, global-transfer, or SCC evidence",
    }
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

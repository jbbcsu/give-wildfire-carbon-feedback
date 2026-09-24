#!/usr/bin/env python3
"""Build fixed cell moderators for a published-response transport benchmark.

This is an alternative-product benchmark, not a reconstruction of the
authors' SAGE/GMFD/subnational moderator panel. Country assignment prioritizes
the crop-location MAPSPAM proxy and uses dominant author-region geometry only
where that proxy is unavailable. Missing PWT income is never imputed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
KEYS = ["native_lat_index", "native_lon_index"]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def choose_pwt_snapshot(frame: pd.DataFrame, target_year: int) -> pd.DataFrame:
    valid = frame.loc[
        frame["pop"].gt(0) & frame["cgdpo"].gt(0),
        ["countrycode", "country", "year", "pop", "cgdpo"],
    ].copy()
    valid["year_distance"] = (valid["year"] - target_year).abs()
    # Prefer the earlier year only in an exact-distance tie; deterministic and
    # avoids assigning information from farther into the future than needed.
    valid = valid.sort_values(["countrycode", "year_distance", "year"])
    selected = valid.drop_duplicates("countrycode", keep="first").copy()
    selected["ln_gdppc"] = np.log(selected["cgdpo"] / selected["pop"])
    require(np.isfinite(selected["ln_gdppc"]).all(), "nonfinite PWT income")
    return selected.rename(columns={"year": "pwt_year"})


def dominant_geometry_country(crosswalk: pd.DataFrame) -> pd.DataFrame:
    frame = crosswalk[KEYS + ["region_key", "intersection_area_equal_area_m2"]].copy()
    frame["geometry_country"] = frame["region_key"].str.slice(0, 3)
    frame = frame.loc[frame["geometry_country"].str.fullmatch(r"[A-Z]{3}", na=False)]
    # Mixed-resolution author regions overlap. Do not sum overlapping regions;
    # retain the largest single intersection observed for each country/cell.
    by_country = (
        frame.groupby(KEYS + ["geometry_country"], as_index=False, sort=False)
        ["intersection_area_equal_area_m2"].max()
    )
    by_country = by_country.sort_values(
        KEYS + ["intersection_area_equal_area_m2", "geometry_country"],
        ascending=[True, True, False, True],
    )
    result = by_country.drop_duplicates(KEYS, keep="first").copy()
    counts = by_country.groupby(KEYS).size().rename("geometry_country_candidates")
    result = result.merge(counts, on=KEYS, how="left", validate="one_to_one")
    return result


def combine_regimes(rainfed: pd.DataFrame, irrigated: pd.DataFrame) -> pd.DataFrame:
    columns = KEYS + ["latitude", "longitude", "mirca_area_ha", "lr_tmax_crop", "lr_prcp_crop"]
    combined = rainfed[columns].merge(
        irrigated[columns], on=KEYS, how="outer", suffixes=("_rainfed", "_irrigated"), validate="one_to_one"
    )
    for coordinate in ("latitude", "longitude"):
        left, right = combined[f"{coordinate}_rainfed"], combined[f"{coordinate}_irrigated"]
        both = left.notna() & right.notna()
        require(np.allclose(left[both], right[both], rtol=0.0, atol=0.0), f"{coordinate} differs by regime")
        combined[coordinate] = left.fillna(right)
    for regime in ("rainfed", "irrigated"):
        combined[f"mirca_area_ha_{regime}"] = combined[f"mirca_area_ha_{regime}"].fillna(0.0)
    combined["mirca_area_ha"] = combined.mirca_area_ha_rainfed + combined.mirca_area_ha_irrigated
    require(combined.mirca_area_ha.gt(0).all(), "zero combined crop area")
    combined["irrigated_share"] = combined.mirca_area_ha_irrigated / combined.mirca_area_ha
    for feature in ("lr_tmax_crop", "lr_prcp_crop"):
        numerator = (
            combined[f"{feature}_rainfed"].fillna(0.0) * combined.mirca_area_ha_rainfed
            + combined[f"{feature}_irrigated"].fillna(0.0) * combined.mirca_area_ha_irrigated
        )
        combined[feature] = numerator / combined.mirca_area_ha
    keep = KEYS + [
        "latitude", "longitude", "mirca_area_ha_rainfed", "mirca_area_ha_irrigated",
        "mirca_area_ha", "irrigated_share", "lr_tmax_crop", "lr_prcp_crop",
    ]
    return combined[keep].sort_values(KEYS).reset_index(drop=True)


def area_fraction(frame: pd.DataFrame, mask: pd.Series) -> float:
    return float(frame.loc[mask, "mirca_area_ha"].sum() / frame["mirca_area_ha"].sum())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rainfed-climatology", type=Path, required=True)
    parser.add_argument("--irrigated-climatology", type=Path, required=True)
    parser.add_argument("--country-proxy", type=Path, required=True)
    parser.add_argument("--region-crosswalk", type=Path, required=True)
    parser.add_argument("--pwt-workbook", type=Path, required=True)
    parser.add_argument("--pwt-target-year", type=int, default=2000)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")

    rainfed = pd.read_parquet(args.rainfed_climatology)
    irrigated = pd.read_parquet(args.irrigated_climatology)
    cells = combine_regimes(rainfed, irrigated)

    proxy = pd.read_parquet(args.country_proxy).rename(columns={"lat": "latitude", "lon_360": "longitude"})
    proxy = proxy.loc[proxy.country_count.eq(1) & proxy.country_label.notna(), ["latitude", "longitude", "country_label"]]
    require(len(proxy) == len(proxy.drop_duplicates(["latitude", "longitude"])), "duplicate unique country proxy")
    cells = cells.merge(proxy, on=["latitude", "longitude"], how="left", validate="one_to_one")

    crosswalk = pd.read_parquet(args.region_crosswalk)
    geometry = dominant_geometry_country(crosswalk)
    cells = cells.merge(geometry, on=KEYS, how="left", validate="one_to_one")
    common = cells.country_label.notna() & cells.geometry_country.notna()
    agreement = cells.country_label.eq(cells.geometry_country)
    cells["country_code"] = cells.country_label.fillna(cells.geometry_country)
    cells["country_source"] = np.select(
        [cells.country_label.notna(), cells.geometry_country.notna()],
        ["mapspam_unique", "dominant_author_geometry"], default="missing",
    )

    pwt = pd.read_excel(
        args.pwt_workbook, sheet_name="Data", usecols=["countrycode", "country", "year", "pop", "cgdpo"]
    )
    income = choose_pwt_snapshot(pwt, args.pwt_target_year)
    cells = cells.merge(
        income[["countrycode", "country", "pwt_year", "year_distance", "pop", "cgdpo", "ln_gdppc"]],
        left_on="country_code", right_on="countrycode", how="left", validate="many_to_one",
    )
    cells["income_available"] = cells.ln_gdppc.notna()
    require(np.isfinite(cells.loc[cells.income_available, ["ln_gdppc"]].to_numpy()).all(), "nonfinite matched income")

    output_columns = KEYS + [
        "latitude", "longitude", "mirca_area_ha_rainfed", "mirca_area_ha_irrigated", "mirca_area_ha",
        "irrigated_share", "lr_tmax_crop", "lr_prcp_crop", "country_code", "country_source",
        "geometry_country_candidates", "pwt_year", "year_distance", "ln_gdppc", "income_available",
    ]
    result = cells[output_columns].sort_values(KEYS).reset_index(drop=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(args.output, index=False, compression="zstd")

    matched = result.income_available
    receipt = {
        "schema": "hultgren_cell_moderators/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "alternative_country_income_and_climate_moderators_not_author_replication",
        "sources": {
            "rainfed_climatology": {"path": str(args.rainfed_climatology), "sha256": digest(args.rainfed_climatology)},
            "irrigated_climatology": {"path": str(args.irrigated_climatology), "sha256": digest(args.irrigated_climatology)},
            "country_proxy": {"path": str(args.country_proxy), "sha256": digest(args.country_proxy)},
            "region_crosswalk": {"path": str(args.region_crosswalk), "sha256": digest(args.region_crosswalk)},
            "pwt": {
                "path": str(args.pwt_workbook), "sha256": digest(args.pwt_workbook),
                "official_url": "https://www.rug.nl/ggdc/docs/pwt100.xlsx",
                "release": "Penn World Table 10.0 workbook distributed on the official University of Groningen site",
                "license": "CC BY 4.0",
                "target_year": args.pwt_target_year,
                "income_definition": "ln(cgdpo/pop), with both variables expressed in millions so the ratio is 2017 US dollars per person",
            },
        },
        "output": {"path": str(args.output), "bytes": args.output.stat().st_size, "sha256": digest(args.output), "rows": len(result)},
        "coverage": {
            "total_crop_area_ha": float(result.mirca_area_ha.sum()),
            "mapspam_unique_country_area_fraction": area_fraction(cells, cells.country_source.eq("mapspam_unique")),
            "geometry_fallback_area_fraction": area_fraction(cells, cells.country_source.eq("dominant_author_geometry")),
            "missing_country_area_fraction": area_fraction(cells, cells.country_source.eq("missing")),
            "pwt_income_available_area_fraction": area_fraction(result, matched),
            "pwt_income_missing_area_fraction": area_fraction(result, ~matched),
            "country_codes_without_pwt": sorted(result.loc[~matched & result.country_code.notna(), "country_code"].unique().tolist()),
            "common_mapspam_geometry_area_fraction": area_fraction(cells, common),
            "common_mapspam_geometry_agreement_area_fraction_of_common": float(
                cells.loc[common & agreement, "mirca_area_ha"].sum() / cells.loc[common, "mirca_area_ha"].sum()
            ) if common.any() else math.nan,
        },
        "interpretation": (
            "fixed alternative-product moderators for a transport benchmark; PWT income is country-level and historical climate is a simple "
            "27-year GSWP3-W5E5 climatology, not the authors' subnational income or time-varying triangular 30-year SAGE/GMFD moderators"
        ),
        "claim_gates": {
            "income_imputed_for_missing_countries": False,
            "author_moderators_reproduced": False,
            "transport_benchmark_ready_on_reported_support": True,
            "damage_or_scc_validated": False,
        },
        "implementation": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "output": receipt["output"], "coverage": receipt["coverage"]}, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Independent streamed audit of GFDL global 21-year centered source features.

No GMT response, yield, damage or SCC is calculated.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from audit_gfdl_2032_2039_maize_crossyear import digest, require
from audit_gfdl_contiguous_28yr_global import OUTPUT as SOURCE_AUDIT, directory
from build_rimex_centered_feature_means import METRICS
from continue_gfdl_global_centered_tiles import BASE, STATUS
from pilot_gfdl_contiguous_global_boundary import BOUNDED
from pilot_gfdl_global_centered_21yr_tile import GMST
from validate_gfdl_2032_maize_global_tiles import SAMPLE_TILE_STARTS


OUT = BASE / "independent_global_centered_audit.json"
KEYS = ["lat", "lon", "crop", "irrigation"]


def sample_reconstruction(start: int, centered: pd.DataFrame,
                          selected: pd.DataFrame, name: str) -> int:
    keys = KEYS + (["stage_id"] if name == "stages" else [])
    features = METRICS + (["stage_days"] if name == "stages" else ["season_days"])
    probes = selected[keys].drop_duplicates()
    require(len(probes) == (9 if name == "stages" else 3),
            f"{start} {name}: sample support changed")
    table = centered.set_index(keys + ["center_year"])
    annual: dict[tuple, list[np.ndarray]] = {
        tuple(row): [] for row in probes.itertuples(index=False, name=None)
    }
    for year in range(2032, 2060):
        source = directory(year) / f"lat{start:03d}_{start + 10:03d}" / f"{name}.parquet"
        frame = pd.read_parquet(source, columns=keys + features).set_index(keys)
        for key in annual:
            value = frame.loc[key, features]
            require(isinstance(value, pd.Series),
                    f"{year} {start} {name}: sample duplicate/missing")
            annual[key].append(value.to_numpy(dtype=float))
    checked = 0
    for key, values in annual.items():
        array = np.vstack(values)
        require(array.shape == (28, len(features)), "annual sample window incomplete")
        for center in (2042, 2049):
            expected = np.mean(array[center - 2042:center - 2042 + 21], axis=0)
            row = table.loc[key + (center,)]
            actual = row[[f"{field}_21yr_mean" for field in features]].to_numpy(dtype=float)
            require(np.allclose(actual, expected, rtol=0, atol=1e-9),
                    f"{start} {name}: independent centered mean differs at {key} {center}")
            checked += 1
    return checked


def main() -> None:
    require(not OUT.exists(), "existing centered global audit needs review")
    source = json.loads(SOURCE_AUDIT.read_text())
    require(source["status"] == "passed_source_only_not_gmt_response_yield_damage_or_scc"
            and source["years"] == list(range(2032, 2060)),
            "annual source audit gate closed")
    manifest_path = BASE / "global_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    require(manifest["schema"] == "gfdl_ssp126_global_maize_centered_21yr_source_tiles_v1"
            and manifest["status"] == "complete_engineering_pending_independent_centered_validation"
            and manifest["source_audit_sha256"] == digest(SOURCE_AUDIT)
            and manifest["center_years"] == list(range(2042, 2050))
            and len(manifest["tiles"]) == 36,
            "centered global manifest malformed")
    reference_gmst = pd.read_parquet(
        BOUNDED / "same_realization_gmst_2042_2049_centered21.parquet")
    require(reference_gmst.center_year.astype(int).tolist() == list(range(2042, 2050)),
            "same-realization centered GMST changed")
    all_keys: set[tuple[int, float, float]] = set()
    total_season = total_stage = samples = 0
    for index, start in enumerate(range(0, 360, 10)):
        tile = BASE / f"lat{start:03d}_{start + 10:03d}"
        receipt = json.loads((tile / "centered_audit_21yr.json").read_text())
        require(receipt == manifest["tiles"][index]
                and receipt["status"] == STATUS
                and receipt["source_audit_sha256"] == digest(SOURCE_AUDIT)
                and receipt["gmst_input_sha256"] == digest(GMST),
                f"{start}: receipt/manifest/source mismatch")
        paths = {name: tile / f"centered_{name}_21yr.parquet"
                 for name in ("season", "stages")}
        require(digest(paths["season"]) == receipt["season_sha256"]
                and digest(paths["stages"]) == receipt["stages_sha256"],
                f"{start}: centered file digest changed")
        season = pd.read_parquet(paths["season"])
        stages = pd.read_parquet(paths["stages"])
        require(len(season) == receipt["season_rows"]
                and len(stages) == receipt["stage_rows"],
                f"{start}: centered support changed")
        base = pd.read_parquet(
            directory(2032) / f"lat{start:03d}_{start + 10:03d}" / "season.parquet",
            columns=["lat", "lon"])
        expected = set(map(tuple, base[["lat", "lon"]].to_numpy()))
        expected_centers = set(range(2042, 2050)) if expected else set()
        require(set(season.center_year) == expected_centers
                and set(stages.center_year) == expected_centers,
                f"{start}: centered years changed")
        require(len(expected) * 8 == len(season)
                and len(stages) == 3 * len(season),
                f"{start}: calendar support count changed")
        for center in range(2042, 2050):
            present = season.loc[season.center_year == center]
            coords = set(map(tuple, present[["lat", "lon"]].to_numpy()))
            require(len(present) == len(coords) == len(expected)
                    and coords == expected,
                    f"{start} {center}: centered calendar keys changed")
            for lat, lon in coords:
                key = (center, float(lat), float(lon))
                require(key not in all_keys, f"duplicate centered cell: {key}")
                all_keys.add(key)
        join_keys = KEYS + ["center_year"]
        grouped = stages.groupby(join_keys).agg(
            rain=("precip_mm_21yr_mean", "sum"),
            wet=("wet_days_n_21yr_mean", "sum"),
            days=("stage_days_21yr_mean", "sum"),
            stage_count=("stage_id", "nunique"))
        merged = season.set_index(join_keys).join(grouped, validate="one_to_one")
        require(len(merged) == len(season)
                and merged.stage_count.eq(3).all(),
                f"{start}: centered stage support failed")
        if len(merged):
            require(np.allclose(merged.precip_mm_21yr_mean, merged.rain, atol=1e-9, rtol=0)
                    and np.allclose(merged.wet_days_n_21yr_mean, merged.wet, atol=1e-12, rtol=0)
                    and np.allclose(merged.season_days_21yr_mean, merged.days, atol=1e-12, rtol=0),
                    f"{start}: centered stage/season reconciliation failed")
        if start in SAMPLE_TILE_STARTS:
            first = season.loc[season.center_year == 2042].sort_values(["lat", "lon"])
            selection = first.iloc[sorted({0, len(first) // 2, len(first) - 1})]
            sample_keys = selection[["lat", "lon"]].drop_duplicates()
            selected_stage = stages.merge(sample_keys, on=["lat", "lon"], how="inner")
            selected_stage = selected_stage.loc[selected_stage.center_year == 2042]
            samples += sample_reconstruction(start, season, selection, "season")
            samples += sample_reconstruction(start, stages, selected_stage, "stages")
        total_season += len(season)
        total_stage += len(stages)
    require(total_season == manifest["season_rows"] == 539360
            and total_stage == manifest["stage_rows"] == 1618080
            and len(all_keys) == total_season and samples == 168,
            "global centered rows or independent sample count failed")
    result = {
        "schema": "gfdl_ssp126_global_maize_centered_21yr_independent_source_audit_v1",
        "status": "passed_centered_source_only_not_gmt_response_yield_damage_or_scc",
        "source_audit_sha256": digest(SOURCE_AUDIT),
        "centered_global_manifest_sha256": digest(manifest_path),
        "center_years": list(range(2042, 2050)),
        "season_rows": total_season, "stage_rows": total_stage,
        "independent_annual_feature_reconstructions": samples,
        "no_yield_data_read": True,
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()

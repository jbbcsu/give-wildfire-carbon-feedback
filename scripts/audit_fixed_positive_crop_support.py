#!/usr/bin/env python3
"""Audit fixed all-case positive support across structural maize models."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import tomllib

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
PHYSICAL = ROOT / "data/interim/epic_caraib_global_comparison_20260908/result.json"
CELLS = ROOT / "data/interim/epic_caraib_geography_20260908/country_cell_production.parquet"
AREA = ROOT / "data/interim/epic_caraib_global_comparison_20260908/common_area_support.parquet"
BASELINE = ROOT / "data/interim/welfare_baseline_ledger_20260914_v2/result.json"
PRICE = ROOT / "config/price_basis_registry.toml"
PROTOCOL = ROOT / "FIXED_POSITIVE_CROP_SUPPORT_PROTOCOL_20260919.md"
DEFAULT_OUTPUT = ROOT / "data/interim/fixed_positive_crop_support_20260919/result.json"
CORNERS = ("y00", "y10", "y01", "y11")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    physical = json.loads(PHYSICAL.read_text())
    baseline = json.loads(BASELINE.read_text())
    with PRICE.open("rb") as f:
        scalar = float(tomllib.load(f)["central_scalar"])

    areas = pq.read_table(AREA).to_pandas()
    areas = areas.loc[areas.common_response, ["latitude", "longitude", "regime", "area_ha"]].copy()
    if areas.duplicated(["latitude", "longitude", "regime"]).any():
        raise ValueError("duplicate common-area key")
    mask = areas[["latitude", "longitude", "regime"]].copy()
    for model in ("CARAIB", "EPIC-TAMU"):
        mask[f"{model}_positive"] = True
        mask[f"{model}_nonfinite"] = False
        mask[f"{model}_nonpositive_finite"] = False

    ledger_bindings = []
    counts = {"CARAIB": 0, "EPIC-TAMU": 0}
    for summary in physical["summaries"]:
        model = summary["crop_model"]
        path = ROOT / summary["ledger_path"]
        if digest(path) != summary["ledger_sha256"]:
            raise ValueError(f"ledger hash mismatch: {path}")
        ledger_bindings.append({"path": summary["ledger_path"], "sha256": summary["ledger_sha256"]})
        frame = pq.read_table(path, columns=["latitude", "longitude", *CORNERS]).to_pandas()
        support_index = mask.index[mask.regime == summary["regime"]]
        support = mask.loc[support_index, ["latitude", "longitude"]].merge(
            frame, on=["latitude", "longitude"], how="left", validate="one_to_one", sort=False
        )
        values = support[list(CORNERS)]
        nonfinite = ~values.map(math.isfinite).all(axis=1)
        nonpositive = values.map(math.isfinite).all(axis=1) & (values <= 0).any(axis=1)
        good = ~(nonfinite | nonpositive)
        mask.loc[support_index, f"{model}_positive"] &= good.to_numpy()
        mask.loc[support_index, f"{model}_nonfinite"] |= nonfinite.to_numpy()
        mask.loc[support_index, f"{model}_nonpositive_finite"] |= nonpositive.to_numpy()
        counts[model] += 1
    if counts != {"CARAIB": 16, "EPIC-TAMU": 16}:
        raise ValueError(f"unexpected model ledger counts: {counts}")
    mask["both_models_positive"] = mask["CARAIB_positive"] & mask["EPIC-TAMU_positive"]
    mask = mask.merge(areas, on=["latitude", "longitude", "regime"], validate="one_to_one")

    cells = pq.read_table(CELLS).to_pandas()
    cells = cells.loc[cells.common_response & (cells.production_mt > 0),
                      ["country", "latitude", "longitude", "regime", "production_mt"]].copy()
    values = {(r["country"], r["regime"]): r for r in baseline["country_regime_rows"]}
    denominators = cells.groupby(["country", "regime"], sort=False).production_mt.sum().to_dict()
    cell_values = []
    for row in cells.itertuples(index=False):
        source = values[(row.country, row.regime)]
        raw = source["common_response_value_proxy_thousand_constant_2014_2016_USD"]
        cell_values.append(None if raw is None else
                           float(raw) * scalar * row.production_mt / denominators[(row.country, row.regime)])
    cells["covered_value_thousand_USD2005"] = cell_values
    cells = cells.merge(mask.drop(columns="area_ha"), on=["latitude", "longitude", "regime"],
                        how="left", validate="many_to_one")
    if cells[["CARAIB_positive", "EPIC-TAMU_positive", "both_models_positive"]].isna().any().any():
        raise ValueError("production cell absent from fixed mask")

    summaries = []
    for mask_name in ("CARAIB_positive", "EPIC-TAMU_positive", "both_models_positive"):
        for regime in ("rainfed", "irrigated", "all"):
            a = mask if regime == "all" else mask.loc[mask.regime == regime]
            c = cells if regime == "all" else cells.loc[cells.regime == regime]
            retained_a = a.loc[a[mask_name]]
            retained_c = c.loc[c[mask_name]]
            total_value = math.fsum(c.covered_value_thousand_USD2005.dropna().tolist())
            retained_value = math.fsum(retained_c.covered_value_thousand_USD2005.dropna().tolist())
            total_prod = math.fsum(c.production_mt.tolist())
            retained_prod = math.fsum(retained_c.production_mt.tolist())
            total_area = math.fsum(a.area_ha.tolist())
            retained_area = math.fsum(retained_a.area_ha.tolist())
            summaries.append({
                "mask": mask_name,
                "regime": regime,
                "total_unique_cells": int(len(a)),
                "retained_unique_cells": int(len(retained_a)),
                "excluded_unique_cells": int(len(a) - len(retained_a)),
                "total_area_ha": total_area,
                "retained_area_ha": retained_area,
                "excluded_area_ha": total_area - retained_area,
                "retained_area_percent": 100 * retained_area / total_area,
                "total_production_mt": total_prod,
                "retained_production_mt": retained_prod,
                "excluded_production_mt": total_prod - retained_prod,
                "retained_production_percent": 100 * retained_prod / total_prod,
                "total_covered_value_thousand_USD2005": total_value,
                "retained_covered_value_thousand_USD2005": retained_value,
                "excluded_covered_value_thousand_USD2005": total_value - retained_value,
                "retained_covered_value_percent": 100 * retained_value / total_value,
            })

    excluded = cells.loc[~cells.both_models_positive].copy()
    country = excluded.groupby("country", as_index=False).agg(
        excluded_production_mt=("production_mt", "sum"),
        excluded_covered_value_thousand_USD2005=("covered_value_thousand_USD2005", "sum"),
        excluded_country_regime_cell_rows=("country", "size"),
    )
    top_production = country.sort_values(["excluded_production_mt", "country"], ascending=[False, True]).head(15)
    top_value = country.sort_values(["excluded_covered_value_thousand_USD2005", "country"],
                                    ascending=[False, True]).head(15)

    reason_counts = []
    for model in ("CARAIB", "EPIC-TAMU"):
        for regime in ("rainfed", "irrigated", "all"):
            a = mask if regime == "all" else mask.loc[mask.regime == regime]
            reason_counts.append({
                "crop_model": model, "regime": regime,
                "unique_cells_with_any_nonfinite_corner": int(a[f"{model}_nonfinite"].sum()),
                "unique_cells_with_any_nonpositive_finite_corner": int(a[f"{model}_nonpositive_finite"].sum()),
            })

    output = {
        "status": "fixed_all_case_positive_support_audit_complete",
        "model_ledger_counts": counts,
        "summaries": summaries,
        "reason_counts": reason_counts,
        "top_both_model_excluded_countries_by_production": top_production.to_dict("records"),
        "top_both_model_excluded_countries_by_value": top_value.to_dict("records"),
        "welfare_recomputed": False,
        "crop_model_repaired": False,
        "empirical_damage_authorized": False,
        "give_export_authorized": False,
        "scc_authorized": False,
        "source_bindings": {
            "physical_result_sha256": digest(PHYSICAL),
            "country_cell_production_sha256": digest(CELLS),
            "common_area_support_sha256": digest(AREA),
            "baseline_value_ledger_sha256": digest(BASELINE),
            "price_registry_sha256": digest(PRICE),
            "protocol_sha256": digest(PROTOCOL),
            "builder_sha256": digest(Path(__file__)),
            "physical_ledgers": sorted({x["path"]: x for x in ledger_bindings}.values(),
                                       key=lambda x: x["path"]),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()

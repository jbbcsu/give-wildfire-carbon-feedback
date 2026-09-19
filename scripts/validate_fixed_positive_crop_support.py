#!/usr/bin/env python3
"""Independent reconstruction of the fixed positive crop-support audit."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import tomllib

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
PHYSICAL = ROOT / "data/interim/epic_caraib_global_comparison_20260908/result.json"
CELLS = ROOT / "data/interim/epic_caraib_geography_20260908/country_cell_production.parquet"
AREA = ROOT / "data/interim/epic_caraib_global_comparison_20260908/common_area_support.parquet"
BASELINE = ROOT / "data/interim/welfare_baseline_ledger_20260914_v2/result.json"
PRICE = ROOT / "config/price_basis_registry.toml"
PROTOCOL = ROOT / "FIXED_POSITIVE_CROP_SUPPORT_PROTOCOL_20260919.md"
BUILDER = ROOT / "scripts/audit_fixed_positive_crop_support.py"
RESULT = ROOT / "data/interim/fixed_positive_crop_support_20260919/result.json"
DEFAULT_OUTPUT = ROOT / "data/interim/fixed_positive_crop_support_validation_20260919/result.json"
CORNERS = ("y00", "y10", "y01", "y11")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def close(a, b, label, checks):
    if not math.isclose(float(a), float(b), rel_tol=3e-12, abs_tol=1e-7):
        raise AssertionError(f"{label}: {a!r} != {b!r}")
    checks.append(label)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    physical = json.loads(PHYSICAL.read_text())
    baseline = json.loads(BASELINE.read_text())
    result = json.loads(RESULT.read_text())
    with PRICE.open("rb") as f:
        scalar = float(tomllib.load(f)["central_scalar"])
    checks = []

    source_ledgers = sorted(
        {r["ledger_path"]: {"path": r["ledger_path"], "sha256": r["ledger_sha256"]}
         for r in physical["summaries"]}.values(), key=lambda x: x["path"]
    )
    bindings = {
        "physical_result_sha256": digest(PHYSICAL),
        "country_cell_production_sha256": digest(CELLS),
        "common_area_support_sha256": digest(AREA),
        "baseline_value_ledger_sha256": digest(BASELINE),
        "price_registry_sha256": digest(PRICE),
        "protocol_sha256": digest(PROTOCOL),
        "builder_sha256": digest(BUILDER),
        "physical_ledgers": source_ledgers,
    }
    if result["source_bindings"] != bindings:
        raise AssertionError("source bindings differ")
    checks.append("source_bindings")
    for flag in ("welfare_recomputed", "crop_model_repaired", "empirical_damage_authorized",
                 "give_export_authorized", "scc_authorized"):
        if result[flag] is not False:
            raise AssertionError(f"{flag} must remain false")
        checks.append(flag)

    area = pq.read_table(AREA).to_pandas()
    area = area.loc[area.common_response, ["latitude", "longitude", "regime", "area_ha"]]
    keys = list(area[["latitude", "longitude", "regime"]].itertuples(index=False, name=None))
    flags = {key: {"CARAIB": True, "EPIC-TAMU": True,
                   "CARAIB_nonfinite": False, "EPIC-TAMU_nonfinite": False,
                   "CARAIB_nonpositive": False, "EPIC-TAMU_nonpositive": False}
             for key in keys}
    ledger_counts = {"CARAIB": 0, "EPIC-TAMU": 0}
    for summary in physical["summaries"]:
        model, regime = summary["crop_model"], summary["regime"]
        frame = pq.read_table(ROOT / summary["ledger_path"],
                              columns=["latitude", "longitude", *CORNERS]).to_pydict()
        lookup = {(lat, lon): tuple(frame[c][i] for c in CORNERS)
                  for i, (lat, lon) in enumerate(zip(frame["latitude"], frame["longitude"]))}
        for key in keys:
            if key[2] != regime:
                continue
            values = lookup[(key[0], key[1])]
            finite = all(math.isfinite(v) for v in values)
            positive = finite and all(v > 0 for v in values)
            flags[key][model] &= positive
            flags[key][f"{model}_nonfinite"] |= not finite
            flags[key][f"{model}_nonpositive"] |= finite and not positive
        ledger_counts[model] += 1
    if ledger_counts != result["model_ledger_counts"]:
        raise AssertionError("model ledger counts differ")
    checks.append("model_ledger_counts")

    cells = pq.read_table(CELLS).to_pandas()
    cells = cells.loc[cells.common_response & (cells.production_mt > 0)]
    baseline_rows = {(r["country"], r["regime"]): r for r in baseline["country_regime_rows"]}
    den = cells.groupby(["country", "regime"]).production_mt.sum().to_dict()
    records = []
    for row in cells.itertuples(index=False):
        key = (row.latitude, row.longitude, row.regime)
        source = baseline_rows[(row.country, row.regime)]
        raw = source["common_response_value_proxy_thousand_constant_2014_2016_USD"]
        records.append({
            "country": row.country, "regime": row.regime, "key": key,
            "production": float(row.production_mt),
            "value": None if raw is None else float(raw) * scalar * row.production_mt / den[(row.country, row.regime)],
        })
    area_lookup = {k: float(a) for k, a in zip(keys, area.area_ha)}
    summary_lookup = {(r["mask"], r["regime"]): r for r in result["summaries"]}
    mask_model = {"CARAIB_positive": "CARAIB", "EPIC-TAMU_positive": "EPIC-TAMU"}
    for mask_name in ("CARAIB_positive", "EPIC-TAMU_positive", "both_models_positive"):
        for regime in ("rainfed", "irrigated", "all"):
            selected_keys = [k for k in keys if regime == "all" or k[2] == regime]
            selected_rows = [r for r in records if regime == "all" or r["regime"] == regime]
            def keep(k):
                if mask_name == "both_models_positive":
                    return flags[k]["CARAIB"] and flags[k]["EPIC-TAMU"]
                return flags[k][mask_model[mask_name]]
            retained_keys = [k for k in selected_keys if keep(k)]
            retained_rows = [r for r in selected_rows if keep(r["key"])]
            total_area = math.fsum(area_lookup[k] for k in selected_keys)
            retained_area = math.fsum(area_lookup[k] for k in retained_keys)
            total_prod = math.fsum(r["production"] for r in selected_rows)
            retained_prod = math.fsum(r["production"] for r in retained_rows)
            total_value = math.fsum(r["value"] for r in selected_rows if r["value"] is not None)
            retained_value = math.fsum(r["value"] for r in retained_rows if r["value"] is not None)
            out = summary_lookup[(mask_name, regime)]
            exact = {
                "total_unique_cells": len(selected_keys),
                "retained_unique_cells": len(retained_keys),
                "excluded_unique_cells": len(selected_keys) - len(retained_keys),
            }
            for name, expected in exact.items():
                if out[name] != expected:
                    raise AssertionError(f"{mask_name}/{regime}/{name}")
                checks.append(f"{mask_name}/{regime}/{name}")
            comparisons = {
                "total_area_ha": total_area, "retained_area_ha": retained_area,
                "excluded_area_ha": total_area-retained_area,
                "retained_area_percent": 100*retained_area/total_area,
                "total_production_mt": total_prod, "retained_production_mt": retained_prod,
                "excluded_production_mt": total_prod-retained_prod,
                "retained_production_percent": 100*retained_prod/total_prod,
                "total_covered_value_thousand_USD2005": total_value,
                "retained_covered_value_thousand_USD2005": retained_value,
                "excluded_covered_value_thousand_USD2005": total_value-retained_value,
                "retained_covered_value_percent": 100*retained_value/total_value,
            }
            for name, expected in comparisons.items():
                close(out[name], expected, f"{mask_name}/{regime}/{name}", checks)

    reasons = {(r["crop_model"], r["regime"]): r for r in result["reason_counts"]}
    for model in ("CARAIB", "EPIC-TAMU"):
        for regime in ("rainfed", "irrigated", "all"):
            selected = [k for k in keys if regime == "all" or k[2] == regime]
            expected = {
                "unique_cells_with_any_nonfinite_corner": sum(flags[k][f"{model}_nonfinite"] for k in selected),
                "unique_cells_with_any_nonpositive_finite_corner": sum(flags[k][f"{model}_nonpositive"] for k in selected),
            }
            out = reasons[(model, regime)]
            for name, value in expected.items():
                if out[name] != value:
                    raise AssertionError(f"{model}/{regime}/{name}")
                checks.append(f"{model}/{regime}/{name}")

    audit = {
        "status": "passed", "check_count": len(checks),
        "validated_result_sha256": digest(RESULT),
        "validator_sha256": digest(Path(__file__)),
        "source_bindings": bindings,
        "welfare_recomputed": False, "give_export_authorized": False, "scc_authorized": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()

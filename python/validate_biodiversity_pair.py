"""Fail-closed audit for matched biodiversity baseline and pulse bundles.

The audit checks accounting mechanics only. It does not calibrate empirical
parameters, estimate damages, discount a marginal path, or calculate an SCC.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from biodiversity_kernel import climate_deficit, country_damage


SCHEMA = "biodiversity_nonuse_pair_v1"
BUNDLE_FIELDS = {"schema", "path_role", "pulse_size_gtc", "first_divergence_year", "rows"}
ROW_FIELDS = {
    "draw_id",
    "climate_realization_id",
    "socioeconomic_draw_id",
    "valuation_draw_id",
    "country_id",
    "year",
    "temperature_change",
    "population",
    "income",
    "no_climate_stock",
    "climate_stock",
    "deficit",
    "beta",
    "damage",
}
DYNAMIC_FIELDS = ("temperature_change", "climate_stock", "deficit", "damage")
PAIRED_FIXED_FIELDS = (
    "climate_realization_id",
    "socioeconomic_draw_id",
    "valuation_draw_id",
    "population",
    "income",
    "no_climate_stock",
    "beta",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite_number(value: object, field: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{field} must be numeric")
    result = float(value)
    require(math.isfinite(result), f"{field} must be finite")
    return result


def index_bundle(bundle: dict[str, object], expected_role: str) -> tuple[dict[tuple[str, str, int], dict[str, object]], int, float]:
    require(set(bundle) == BUNDLE_FIELDS, f"{expected_role} bundle schema changed")
    require(bundle.get("schema") == SCHEMA, f"{expected_role} schema changed")
    require(bundle.get("path_role") == expected_role, f"expected {expected_role} path role")
    first_divergence_year = bundle.get("first_divergence_year")
    require(isinstance(first_divergence_year, int) and not isinstance(first_divergence_year, bool),
            "first_divergence_year must be an integer")
    pulse_size = finite_number(bundle.get("pulse_size_gtc"), "pulse_size_gtc")
    require(pulse_size >= 0, "pulse_size_gtc must be nonnegative")
    if expected_role == "baseline":
        require(pulse_size == 0, "baseline pulse_size_gtc must be zero")
    rows = bundle.get("rows")
    require(isinstance(rows, list) and rows, f"{expected_role} rows are missing")
    indexed: dict[tuple[str, str, int], dict[str, object]] = {}
    for row in rows:
        require(isinstance(row, dict) and set(row) == ROW_FIELDS, f"{expected_role} row schema changed")
        draw_id = row["draw_id"]
        country_id = row["country_id"]
        year = row["year"]
        require(isinstance(draw_id, str) and draw_id.strip(), "draw_id must be nonblank")
        require(isinstance(country_id, str) and country_id.strip(), "country_id must be nonblank")
        require(isinstance(year, int) and not isinstance(year, bool), "year must be an integer")
        for field in ROW_FIELDS - {"draw_id", "country_id", "year", "climate_realization_id", "socioeconomic_draw_id", "valuation_draw_id"}:
            finite_number(row[field], field)
        for field in ("climate_realization_id", "socioeconomic_draw_id", "valuation_draw_id"):
            require(isinstance(row[field], str) and row[field].strip(), f"{field} must be nonblank")
        expected_deficit = climate_deficit(float(row["no_climate_stock"]), float(row["climate_stock"]))
        require(math.isclose(float(row["deficit"]), expected_deficit, rel_tol=0, abs_tol=1e-12),
                "reported deficit does not reproduce")
        expected_damage = country_damage(
            float(row["population"]),
            float(row["income"]),
            float(row["climate_stock"]),
            float(row["deficit"]),
            beta=float(row["beta"]),
        )
        require(math.isclose(float(row["damage"]), expected_damage, rel_tol=1e-12, abs_tol=1e-9),
                "reported damage does not reproduce")
        key = (draw_id, country_id, year)
        require(key not in indexed, f"{expected_role} duplicates draw-country-year key")
        indexed[key] = row
    return indexed, first_divergence_year, pulse_size


def audit_pair(baseline: dict[str, object], pulse: dict[str, object]) -> dict[str, object]:
    baseline_rows, baseline_divergence, baseline_size = index_bundle(baseline, "baseline")
    pulse_rows, pulse_divergence, pulse_size = index_bundle(pulse, "pulse")
    require(baseline_divergence == pulse_divergence, "first-divergence declarations differ")
    require(set(baseline_rows) == set(pulse_rows), "baseline and pulse keys differ")
    years = {key[2] for key in baseline_rows}
    require(any(year < baseline_divergence for year in years), "no pre-divergence year is represented")
    require(any(year >= baseline_divergence for year in years), "no divergence-or-later year is represented")

    maximum_differences = {field: 0.0 for field in DYNAMIC_FIELDS}
    for key, baseline_row in baseline_rows.items():
        pulse_row = pulse_rows[key]
        for field in PAIRED_FIXED_FIELDS:
            require(baseline_row[field] == pulse_row[field], f"paired fixed field differs: {field}")
        for field in DYNAMIC_FIELDS:
            difference = abs(float(pulse_row[field]) - float(baseline_row[field]))
            maximum_differences[field] = max(maximum_differences[field], difference)
            if key[2] < baseline_divergence:
                require(difference == 0, f"pre-divergence identity failed: {field}")
            if pulse_size == 0:
                require(difference == 0, f"zero-pulse identity failed: {field}")

    return {
        "schema": "biodiversity_nonuse_pair_audit_v1",
        "status": "passed_accounting_mechanics_only",
        "row_count_per_path": len(baseline_rows),
        "draw_count": len({key[0] for key in baseline_rows}),
        "country_count": len({key[1] for key in baseline_rows}),
        "year_count": len(years),
        "first_divergence_year": baseline_divergence,
        "baseline_pulse_size_gtc": baseline_size,
        "pulse_size_gtc": pulse_size,
        "matched_keys": True,
        "matched_fixed_inputs": True,
        "recomputed_deficits_and_damages": True,
        "pre_divergence_identity": True,
        "zero_pulse_identity": pulse_size == 0,
        "maximum_absolute_path_differences": maximum_differences,
        "empirical_parameters_validated": False,
        "welfare_overlap_validated": False,
        "discounting_validated": False,
        "damage_or_scc_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--pulse", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit_pair(
        json.loads(args.baseline.read_text(encoding="utf-8")),
        json.loads(args.pulse.read_text(encoding="utf-8")),
    )
    result["inputs"] = {
        "baseline": {"path": str(args.baseline.resolve()), "sha256": sha256(args.baseline)},
        "pulse": {"path": str(args.pulse.resolve()), "sha256": sha256(args.pulse)},
    }
    implementation = Path(__file__).resolve()
    result["implementation"] = {"path": str(implementation), "sha256": sha256(implementation)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix(args.out.suffix + ".partial")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.out)
    print(f"biodiversity pair audit passed: {result['row_count_per_path']} rows per path")


if __name__ == "__main__":
    main()

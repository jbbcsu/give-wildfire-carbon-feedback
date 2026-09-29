#!/usr/bin/env python3
"""Independently rebuild the sorghum/cotton all-practice benchmark audit."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
YEARS = tuple(range(1981, 2019))
CROPS = {
    "sorghum_grain": ("SORGHUM", "ALL CLASSES", "GRAIN", "BU / ACRE"),
    "cotton_upland": (
        "COTTON", "UPLAND", "ALL UTILIZATION PRACTICES", "LB / ACRE",
    ),
}
KEYS = ["crop", "harvest_year", "county_geoid"]


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def project_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("paths must be project-relative")
    resolved = (ROOT / path).resolve()
    resolved.relative_to(ROOT.resolve())
    return resolved


def numeric_positive(value: object) -> float:
    text = str(value).strip().replace(",", "")
    if not re.fullmatch(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", text):
        return float("nan")
    parsed = float(text)
    return parsed if np.isfinite(parsed) and parsed > 0 else float("nan")


def expected_query(crop: str, year: int) -> dict[str, str]:
    commodity, crop_class, utilization, unit = CROPS[crop]
    return {
        "source_desc": "SURVEY", "sector_desc": "CROPS",
        "commodity_desc": commodity, "class_desc": crop_class,
        "util_practice_desc": utilization, "unit_desc": unit,
        "statisticcat_desc": "YIELD", "agg_level_desc": "COUNTY",
        "freq_desc": "ANNUAL", "reference_period_desc": "YEAR",
        "domain_desc": "TOTAL", "prodn_practice_desc": "ALL PRODUCTION PRACTICES",
        "year": str(year), "format": "JSON",
    }


def qstats(values: np.ndarray) -> dict[str, float]:
    if len(values) == 0:
        return {name: 0.0 for name in ("q50", "q90", "q95", "q99", "maximum")}
    return {
        "q50": float(np.quantile(values, 0.50)),
        "q90": float(np.quantile(values, 0.90)),
        "q95": float(np.quantile(values, 0.95)),
        "q99": float(np.quantile(values, 0.99)),
        "maximum": float(np.max(values)),
    }


def classify(share: float) -> str:
    return "broad" if share >= 0.5 else "selected" if share >= 0.2 else "highly_selected"


def dimension_rows(
    universe: pd.DataFrame, direct: pd.DataFrame, matched: pd.DataFrame, field: str,
) -> list[dict[str, Any]]:
    values: list[Any]
    if field == "harvest_year":
        values = list(YEARS)
    else:
        values = sorted(set(universe.state_alpha.astype(str)) | set(direct.state_alpha.astype(str)))
    output = []
    for value in values:
        if field == "harvest_year":
            all_n = int((universe.harvest_year == value).sum())
            direct_n = int((direct.harvest_year == value).sum())
            match_n = int((matched.harvest_year == value).sum())
        else:
            all_n = int(universe.state_alpha.astype(str).eq(value).sum())
            direct_n = int(direct.state_alpha.astype(str).eq(value).sum())
            match_n = int(matched.state_alpha.astype(str).eq(value).sum())
        output.append({
            field: value,
            "all_practice_positive_county_years": all_n,
            "direct_practice_paired_county_years": direct_n,
            "matched_county_years": match_n,
            "paired_share_of_all_practice": None if all_n == 0 else direct_n / all_n,
            "benchmark_match_share_of_direct_pairs": None if direct_n == 0 else match_n / direct_n,
        })
    return output


def independently_summarize(
    crop: str, universe: pd.DataFrame, paired_long: pd.DataFrame,
) -> dict[str, Any]:
    direct = (
        paired_long.set_index(KEYS + ["state_alpha", "practice"])["yield_value"]
        .unstack("practice").reset_index()
    )
    aggregate = universe[KEYS + ["yield_unit", "yield_value"]].rename(
        columns={"yield_value": "all_practice_yield"}
    )
    matched = direct.merge(aggregate, on=KEYS, how="inner", validate="one_to_one")
    matched = matched.merge(
        direct[KEYS + ["state_alpha"]], on=KEYS, how="left",
        validate="one_to_one", suffixes=("", "_copy"),
    )
    if "state_alpha_copy" in matched:
        matched.drop(columns="state_alpha_copy", inplace=True)
    if set(universe.yield_unit) != {CROPS[crop][3]} or set(paired_long.yield_unit) != {CROPS[crop][3]}:
        raise ValueError(f"{crop}: unit mismatch")
    lower = matched[["irrigated", "non_irrigated"]].min(axis=1).to_numpy(dtype=float)
    upper = matched[["irrigated", "non_irrigated"]].max(axis=1).to_numpy(dtype=float)
    irr = matched.irrigated.to_numpy(dtype=float)
    non = matched.non_irrigated.to_numpy(dtype=float)
    total = matched.all_practice_yield.to_numpy(dtype=float)
    below = total < lower
    above = total > upper
    equal_both = (total == irr) & (total == non)
    equal_irr = (total == irr) & ~equal_both
    equal_non = (total == non) & ~equal_both
    between = (total > lower) & (total < upper)
    tolerance = np.maximum(0.5, 0.001 * total)
    tolerant = (total >= lower - tolerance) & (total <= upper + tolerance)
    distance = np.maximum.reduce((lower - total, total - upper, np.zeros(len(total))))
    direct_n, all_n, matched_n = len(direct), len(universe), len(matched)
    coverage = matched_n / all_n
    all_states = sorted(map(str, universe.state_alpha.unique()))
    direct_states = sorted(map(str, direct.state_alpha.unique()))
    return {
        "crop": crop,
        "unit": CROPS[crop][3],
        "all_practice_universe": {
            "positive_coded_county_years": all_n,
            "counties": int(universe.county_geoid.nunique()),
            "states": int(universe.state_alpha.nunique()),
            "years_with_positive_rows": int(universe.harvest_year.nunique()),
        },
        "direct_practice_sample": {
            "paired_county_years": direct_n,
            "counties": int(direct.county_geoid.nunique()),
            "states": int(direct.state_alpha.nunique()),
        },
        "benchmark_overlap": {
            "matched_county_years": matched_n,
            "match_fraction_of_direct_pairs": matched_n / direct_n,
            "paired_share_of_all_practice_universe": coverage,
            "selection_classification": classify(coverage),
            "source_coherence_support_gate_passed": matched_n / direct_n >= 0.90,
        },
        "state_support": {
            "all_practice_states": all_states,
            "direct_practice_states": direct_states,
            "all_practice_states_absent_from_direct_sample": sorted(set(all_states) - set(direct_states)),
        },
        "yield_interval_coherence": {
            "matched_county_years": matched_n,
            "below_exact_interval": int(below.sum()),
            "equal_both_practices": int(equal_both.sum()),
            "equal_irrigated_only": int(equal_irr.sum()),
            "equal_non_irrigated_only": int(equal_non.sum()),
            "strictly_between": int(between.sum()),
            "above_exact_interval": int(above.sum()),
            "exact_interval_share": float((~(below | above)).mean()),
            "rounding_tolerant_interval_share": float(tolerant.mean()),
            "rounding_tolerant_bracket_gate_passed": bool(tolerant.mean() >= 0.95),
            "outside_exact_interval_distance_units": qstats(distance),
            "positive_distance_violation_count": int((distance > 0).sum()),
        },
        "annual_support": dimension_rows(universe, direct, matched, "harvest_year"),
        "state_support_detail": dimension_rows(universe, direct, matched, "state_alpha"),
    }


def check_resource(path: Path) -> int:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if (
        receipt.get("status") != "command_completed"
        or int(receipt.get("returncode", -1)) != 0
        or int(receipt.get("peak_rss_bytes", 2**63)) > 512 * 1024 * 1024
    ):
        raise ValueError(f"resource receipt failed: {path}")
    return int(receipt["peak_rss_bytes"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquisition", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--paired-panel", required=True)
    parser.add_argument("--acquisition-resource", required=True)
    parser.add_argument("--audit-resource", required=True)
    parser.add_argument("--secrets", default=".secrets/nass.env")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    acquisition_path = project_path(args.acquisition)
    audit_path = project_path(args.audit)
    paired_path = project_path(args.paired_panel)
    out_path = project_path(args.out)
    if out_path.exists() or not out_path.is_relative_to((ROOT / "data/provenance").resolve()):
        raise ValueError("fresh validation provenance output required")
    acquisition = json.loads(acquisition_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if acquisition.get("schema") != "nass_sorghum_cotton_all_practice_acquisition_v1":
        raise ValueError("wrong acquisition schema")
    if audit.get("schema") != "nass_sorghum_cotton_all_practice_benchmark_audit_v1":
        raise ValueError("wrong audit schema")
    for record in (acquisition["protocol"], acquisition["implementation"]):
        if digest(project_path(record["path"])) != record["sha256"]:
            raise ValueError(f"acquisition identity changed: {record['path']}")
    for record in audit["inputs"].values():
        if digest(project_path(record["path"])) != record["sha256"]:
            raise ValueError(f"audit identity changed: {record['path']}")
    for field in (
        "weather_or_drought_index_read", "direct_weather_and_pdsi_spei_families_combined",
        "coefficients_or_predictions_emitted", "causal_claim_authorized",
        "irrigation_treatment_claim_authorized", "national_representativeness_claim_authorized",
        "future_or_global_transfer_authorized", "damage_claim_authorized", "scc_claim_authorized",
    ):
        if audit.get(field) is not False:
            raise ValueError(f"audit unexpectedly opens {field}")

    expected_record_keys = {(crop, year) for crop in CROPS for year in YEARS}
    actual_record_keys = {(row["crop"], int(row["year"])) for row in acquisition["records"]}
    if actual_record_keys != expected_record_keys or len(acquisition["records"]) != 76:
        raise ValueError("acquisition request matrix differs")
    all_rows = []
    raw_audits = []
    for record in acquisition["records"]:
        crop, year = str(record["crop"]), int(record["year"])
        if record["query_parameters_excluding_key"] != expected_query(crop, year):
            raise ValueError("key-free benchmark query differs")
        path = project_path(record["raw_path"])
        if digest(path, "sha512") != record["sha512"]:
            raise ValueError("raw benchmark hash differs")
        data = json.loads(path.read_text(encoding="utf-8")).get("data")
        if not isinstance(data, list) or len(data) != int(record["count"]):
            raise ValueError("raw benchmark row count differs")
        positive = 0
        for row in data:
            state = str(row.get("state_ansi", "")).strip()
            county = str(row.get("county_ansi", "")).strip()
            value = numeric_positive(row.get("Value", ""))
            if re.fullmatch(r"\d{2}", state) and re.fullmatch(r"\d{3}", county) and np.isfinite(value):
                positive += 1
                all_rows.append({
                    "crop": crop, "harvest_year": year,
                    "county_geoid": state + county,
                    "state_alpha": str(row.get("state_alpha", "")).strip(),
                    "yield_unit": str(row.get("unit_desc", "")).strip(),
                    "yield_value": value,
                })
        raw_audits.append({
            "crop": crop, "year": year, "raw_rows": len(data),
            "positive_coded_rows": positive,
        })
    universe = pd.DataFrame(all_rows)
    if universe.duplicated(KEYS).any():
        raise ValueError("independent benchmark has duplicate keys")
    paired = pd.read_parquet(paired_path)
    if paired.duplicated(KEYS + ["practice"]).any():
        raise ValueError("paired panel duplicates keys")
    rebuilt = [
        independently_summarize(
            crop, universe.loc[universe.crop.eq(crop)].copy(),
            paired.loc[paired.crop.eq(crop)].copy(),
        )
        for crop in CROPS
    ]
    if raw_audits != audit["raw_file_audits"] or rebuilt != audit["crop_summaries"]:
        raise ValueError("independent aggregate reconstruction differs")

    secrets_path = project_path(args.secrets)
    secret_values = []
    for line in secrets_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            name, value = stripped.split("=", 1)
            if name.strip() in {"NASS_API_KEY", "QUICKSTATS_API_KEY"}:
                secret_values.append(value.strip().strip("'\""))
    tracked_text = acquisition_path.read_text(encoding="utf-8") + audit_path.read_text(encoding="utf-8")
    if any(value and value in tracked_text for value in secret_values):
        raise ValueError("credential appears in tracked benchmark artifacts")

    acquisition_rss = check_resource(project_path(args.acquisition_resource))
    audit_rss = check_resource(project_path(args.audit_resource))
    output = {
        "schema": "nass_sorghum_cotton_all_practice_benchmark_validation_v1",
        "status": "passed_independent_raw_reparse_and_aggregate_reconstruction",
        "inputs": {
            "acquisition": {"path": args.acquisition, "sha256": digest(acquisition_path)},
            "audit": {"path": args.audit, "sha256": digest(audit_path)},
            "paired_panel": {"path": args.paired_panel, "sha256": digest(paired_path)},
        },
        "raw_responses_reparsed": 76,
        "raw_rows_reparsed": int(sum(row["raw_rows"] for row in raw_audits)),
        "positive_coded_rows_reconstructed": int(len(universe)),
        "crop_summaries_exactly_reconstructed": True,
        "credential_found_in_tracked_artifacts": False,
        "acquisition_peak_rss_bytes": acquisition_rss,
        "audit_peak_rss_bytes": audit_rss,
        "stronger_claim_gates_all_closed": True,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": output["status"],
        "raw_rows_reparsed": output["raw_rows_reparsed"],
        "positive_coded_rows_reconstructed": output["positive_coded_rows_reconstructed"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()

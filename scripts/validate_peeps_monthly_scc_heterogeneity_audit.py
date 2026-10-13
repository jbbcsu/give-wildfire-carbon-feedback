#!/usr/bin/env python3
"""Independent standard-library validation of the PEEPS heterogeneity audit."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import resource
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


VALUE = "partial_scc_component_usd2020_per_tco2"
CHANNELS = ("joint_monthly_pattern", "quantity_reference", "timing_increment")


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def read_rows(path: Path, entity: str) -> list[dict[str, object]]:
    rows = []
    with path.open(newline="", encoding="utf-8") as stream:
        for raw in csv.DictReader(stream):
            rows.append({
                entity: raw[entity],
                "fund_region": raw["fund_region"],
                "pulse_size_gtc": float(raw["pulse_size_gtc"]),
                "adaptation": raw["adaptation"],
                "discount_rate_label": raw["discount_rate_label"],
                "channel": raw["channel"],
                VALUE: float(raw[VALUE]),
            })
    require(rows and all(math.isfinite(float(row[VALUE])) for row in rows), f"{entity} table is empty or nonfinite")
    return rows


def signed(values: list[float]) -> dict[str, float | int | None]:
    positive = sum(value for value in values if value > 0)
    negative = sum(value for value in values if value < 0)
    gross = positive + abs(negative)
    net = sum(values)
    smaller, dominant = min(positive, abs(negative)), max(positive, abs(negative))
    return {
        "net": net,
        "gross_positive": positive,
        "gross_negative": negative,
        "gross_absolute": gross,
        "positive_count": sum(value > 0 for value in values),
        "negative_count": sum(value < 0 for value in values),
        "zero_count": sum(value == 0 for value in values),
        "absolute_net_share_of_gross_absolute": abs(net) / gross,
        "cancellation_fraction_of_gross_absolute": 1.0 - abs(net) / gross,
        "opposing_side_share_of_dominant_side": smaller / dominant if dominant else 0.0,
        "gross_absolute_to_absolute_net_multiple": gross / abs(net) if net else None,
    }


def close(left: float, right: float, tolerance: float = 1e-12) -> bool:
    return abs(left - right) <= tolerance * max(1.0, abs(left), abs(right))


def compare_metrics(observed: dict[str, object], expected: dict[str, float | int | None], label: str) -> None:
    for key, value in expected.items():
        actual = observed[key]
        if isinstance(value, int):
            require(actual == value, f"{label} {key} differs")
        elif value is None:
            require(actual is None, f"{label} {key} differs")
        else:
            require(close(float(actual), float(value)), f"{label} {key} differs")


def select_central(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    minimum = min(float(row["pulse_size_gtc"]) for row in rows)
    return [
        row for row in rows
        if float(row["pulse_size_gtc"]) == minimum
        and row["adaptation"] == "fixed"
        and row["discount_rate_label"] == "2.0%"
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--country", type=Path, required=True)
    parser.add_argument("--region", type=Path, required=True)
    parser.add_argument("--source-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--memory-cap-bytes", type=int, default=536870912)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh heterogeneity validation output required")
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    source = json.loads(args.source_receipt.read_text(encoding="utf-8"))
    require(audit["schema"] == "peeps_monthly_scc_heterogeneity_audit/v1", "audit schema differs")
    require(audit["sources"]["source_receipt"]["sha256"] == digest(args.source_receipt), "source receipt hash differs")
    require(audit["sources"]["country"]["sha256"] == source["outputs"]["country"]["sha256"] == digest(args.country), "country hash differs")
    require(audit["sources"]["region"]["sha256"] == source["outputs"]["region"]["sha256"] == digest(args.region), "region hash differs")
    implementation_path = Path(audit["implementation"]["path"])
    require(audit["implementation"]["sha256"] == digest(implementation_path), "audit implementation hash differs")

    country = read_rows(args.country, "iso3")
    region = read_rows(args.region, "fund_region")
    require(len(country) == source["support"]["country_rows"] and len(region) == source["support"]["region_rows"], "source row support differs")
    central_country, central_region = select_central(country), select_central(region)
    require(len(central_country) == 107 * 3 and len(central_region) == 17 * 3, "central support differs")
    for channel in CHANNELS:
        country_values = [float(row[VALUE]) for row in central_country if row["channel"] == channel]
        region_values = [float(row[VALUE]) for row in central_region if row["channel"] == channel]
        fund_values = [float(row[VALUE]) for row in central_region if row["channel"] == channel and row["fund_region"] != "UNMAPPED"]
        compare_metrics(audit["central_design"]["country"][channel], signed(country_values), f"country {channel}")
        compare_metrics(audit["central_design"]["region_including_unmapped"][channel], signed(region_values), f"region {channel}")
        compare_metrics(audit["central_design"]["fund_region_excluding_unmapped"][channel], signed(fund_values), f"FUND region {channel}")

    joint_country = [row for row in central_country if row["channel"] == "joint_monthly_pattern"]
    joint_region = [row for row in central_region if row["channel"] == "joint_monthly_pattern"]
    country_values = [float(row[VALUE]) for row in joint_country]
    region_values = [float(row[VALUE]) for row in joint_region]
    gross_country = sum(abs(value) for value in country_values)
    gross_region = sum(abs(value) for value in region_values)
    absolute_net = abs(sum(country_values))
    decomposition = audit["central_design"]["joint_cancellation_decomposition"]
    expected_decomposition = {
        "country_gross_absolute": gross_country,
        "region_gross_absolute_including_unmapped": gross_region,
        "absolute_global_net": absolute_net,
        "within_region_country_netting_amount": gross_country - gross_region,
        "between_region_netting_amount": gross_region - absolute_net,
        "total_netting_amount": gross_country - absolute_net,
        "within_region_share_of_country_gross_absolute": (gross_country - gross_region) / gross_country,
        "between_region_share_of_country_gross_absolute": (gross_region - absolute_net) / gross_country,
        "total_cancellation_fraction_of_country_gross_absolute": (gross_country - absolute_net) / gross_country,
    }
    for key, value in expected_decomposition.items():
        require(close(float(decomposition[key]), value), f"cancellation decomposition {key} differs")

    by_country: dict[str, dict[str, float]] = defaultdict(dict)
    for row in central_country:
        by_country[str(row["iso3"])][str(row["channel"])] = float(row[VALUE])
    require(all(set(values) == set(CHANNELS) for values in by_country.values()), "country channel support differs")
    timing = audit["central_design"]["timing_quantity_interaction"]
    products = [values["quantity_reference"] * values["timing_increment"] for values in by_country.values()]
    expected_timing = {
        "timing_amplifies_quantity_sign_countries": sum(value > 0 for value in products),
        "timing_offsets_quantity_sign_countries": sum(value < 0 for value in products),
        "timing_or_quantity_exact_zero_countries": sum(value == 0 for value in products),
        "timing_changes_quantity_to_joint_sign_countries": sum(
            math.copysign(1, values["quantity_reference"]) != math.copysign(1, values["joint_monthly_pattern"])
            for values in by_country.values()
        ),
        "gross_absolute_timing_share_of_gross_absolute_joint": sum(abs(values["timing_increment"]) for values in by_country.values()) / gross_country,
        "countries_where_absolute_timing_exceeds_absolute_quantity": sum(abs(values["timing_increment"]) > abs(values["quantity_reference"]) for values in by_country.values()),
        "countries_where_absolute_timing_exceeds_absolute_joint": sum(abs(values["timing_increment"]) > abs(values["joint_monthly_pattern"]) for values in by_country.values()),
    }
    for key, value in expected_timing.items():
        actual = timing[key]
        require(actual == value if isinstance(value, int) else close(float(actual), value), f"timing interaction {key} differs")

    grouped: dict[tuple[float, str, str, str], list[float]] = defaultdict(list)
    for row in country:
        key = (float(row["pulse_size_gtc"]), str(row["adaptation"]), str(row["discount_rate_label"]), str(row["channel"]))
        grouped[key].append(float(row[VALUE]))
    for channel in CHANNELS:
        fractions = [signed(values)["cancellation_fraction_of_gross_absolute"] for key, values in grouped.items() if key[-1] == channel]
        reported = audit["all_registered_design_cells"]["country"][channel]
        require(len(fractions) == reported["design_cells"] == 36, f"{channel} design-cell count differs")
        require(close(float(reported["cancellation_fraction_minimum"]), min(fractions)), f"{channel} minimum cancellation differs")
        require(close(float(reported["cancellation_fraction_median"]), statistics.median(fractions)), f"{channel} median cancellation differs")
        require(close(float(reported["cancellation_fraction_maximum"]), max(fractions)), f"{channel} maximum cancellation differs")

    claims = audit["claim_gates"]
    require(claims["accounting_decomposition"] is True, "accounting gate is closed")
    require(not any(value for key, value in claims.items() if key != "accounting_decomposition"), "a scientific promotion gate is open")
    require(audit["resources"]["memory_gate_passed"] is True and audit["resources"]["peak_rss_bytes"] < int(args.memory_cap_bytes), "audit memory gate failed")
    rss = peak_rss_bytes()
    require(rss < int(args.memory_cap_bytes), "heterogeneity validator memory cap exceeded")
    implementation = Path(__file__).resolve()
    result = {
        "schema": "peeps_monthly_scc_heterogeneity_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_country_and_fund_region_cancellation_accounting",
        "checks": {
            "source_hashes_verified": True,
            "central_country_signed_metrics_recomputed": True,
            "central_region_signed_metrics_recomputed": True,
            "fund_region_unmapped_boundary_recomputed": True,
            "within_and_between_region_cancellation_recomputed": True,
            "timing_quantity_interactions_recomputed": True,
            "all_36_country_design_cells_recomputed": True,
            "claim_gates_closed": True,
        },
        "bindings": {
            "audit": {"path": str(args.audit), "sha256": digest(args.audit)},
            "country": {"path": str(args.country), "sha256": digest(args.country)},
            "region": {"path": str(args.region), "sha256": digest(args.region)},
            "source_receipt": {"path": str(args.source_receipt), "sha256": digest(args.source_receipt)},
        },
        "resources": {"peak_rss_bytes": rss, "memory_cap_bytes": int(args.memory_cap_bytes), "memory_gate_passed": True},
        "implementation": {"path": str(implementation), "sha256": digest(implementation)},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": result["checks"], "resources": result["resources"]}, indent=2))


if __name__ == "__main__":
    main()

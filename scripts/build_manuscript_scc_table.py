#!/usr/bin/env python3
"""Build manuscript Table 3 from checksum-bound SCC result receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def money(value: float, digits: int = 5) -> str:
    sign = "-" if value < 0 else "+"
    return f"{sign}{abs(value):.{digits}f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--structural", type=Path, required=True)
    parser.add_argument("--coefficient-grid", type=Path, required=True)
    parser.add_argument("--market-grid", type=Path, required=True)
    parser.add_argument("--country", type=Path, required=True)
    parser.add_argument("--period-grid", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")
    structural = json.loads(args.structural.read_text())
    coefficient = json.loads(args.coefficient_grid.read_text())
    market = json.loads(args.market_grid.read_text())
    country = json.loads(args.country.read_text())
    period_grid = json.loads(args.period_grid.read_text())
    require(structural["schema"] == "quantity_structural_sensitivity_envelope/v1", "structural schema differs")
    require(coefficient["schema"] == "quantity_coefficient_delta_uncertainty_grid/v1", "coefficient schema differs")
    require(market["schema"] == "quantity_coefficient_delta_market_grid/v1", "market schema differs")
    require(country["schema"] == "quantity_scc_country_decomposition/v1", "country schema differs")
    require(period_grid["schema"] == "quantity_scc_period_discount_grid/v1", "period-grid schema differs")
    rates = ["1.5%", "2.0%", "2.5%", "3.0%"]
    coefficient_by_rate = {row["discount_rate_label"]: row for row in coefficient["results"]}
    require(list(coefficient_by_rate) == rates, "discount schedule order differs")

    lines = [
        "# Table 3. Paired annual-maize rainfall-quantity SCC results",
        "",
        "All values are 2020 USD per tCO2. Negative values denote modeled benefits.",
        "Coefficient intervals are first-order normal intervals for the published response coefficients only.",
        "Design percentiles summarize equally weighted registered structural cells and are not probability intervals.",
        "",
        "## Panel A. Discount schedules and uncertainty objects",
        "",
        "| GIVE schedule | Central mean | Coefficient-only SE | Coefficient-only 95% interval | Structural-design mean | Structural 2.5th--97.5th percentile | Negative design cells |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for rate in rates:
        c = coefficient_by_rate[rate]
        s = structural["overall"][rate]
        interval = c["normal_approximation_95_interval_usd2020_per_tco2"]
        lines.append(
            f"| {rate} | {money(c['central_mean_usd2020_per_tco2'])} | "
            f"{c['coefficient_only_delta_standard_error_usd2020_per_tco2']:.5f} | "
            f"[{money(interval[0])}, {money(interval[1])}] | {money(s['mean_usd2020_per_tco2'])} | "
            f"[{money(s['p02_5_usd2020_per_tco2'])}, {money(s['p97_5_usd2020_per_tco2'])}] | "
            f"{s['negative_cells']} / {s['cells']} |"
        )

    lines.extend([
        "",
        "## Panel B. Adaptation choices within the 2% structural design",
        "",
        "| Adaptation | Mean | Design 2.5th--97.5th percentile | Negative cells |",
        "|---|---:|---:|---:|",
    ])
    for adaptation in ("fixed", "trend", "upper"):
        row = structural["dimension_conditionals"]["adaptation"]["2.0%"][adaptation]
        lines.append(
            f"| {adaptation.title()} | {money(row['mean_usd2020_per_tco2'])} | "
            f"[{money(row['p02_5_usd2020_per_tco2'])}, {money(row['p97_5_usd2020_per_tco2'])}] | "
            f"{row['negative_cells']} / {row['cells']} |"
        )

    lines.extend([
        "",
        "## Panel C. Fixed-adaptation, uncapped 2% market cases",
        "",
        "| Supply / demand | Yield-to-supply mapping | Mean | Coefficient-only SE | Coefficient-only 95% interval |",
        "|---|---|---:|---:|---:|",
    ])
    for row in market["results"]:
        interval = row["normal_approximation_95_interval_usd2020_per_tco2"]
        mapping = row["yield_to_supply_mapping"].replace("_", " ").title()
        lines.append(
            f"| {row['supply_elasticity']:.2f} / {row['demand_elasticity_magnitude']:.2f} | {mapping} | "
            f"{money(row['central_equal_model_mean_usd2020_per_tco2'])} | "
            f"{row['coefficient_only_delta_standard_error_usd2020_per_tco2']:.5f} | "
            f"[{money(interval[0])}, {money(interval[1])}] |"
        )
    country_summary = country["summary"]
    lines.extend([
        "",
        "## Panel D. Geographic concentration of the central 2% case",
        "",
        "| Accounting diagnostic | Value |",
        "|---|---:|",
        f"| Country means below / above zero | {country_summary['negative_country_count']} / {country_summary['positive_country_count']} |",
        f"| Country components changing sign across climate models | {country_summary['country_components_changing_sign_across_models']} / {country_summary['countries']} |",
        f"| U.S. + China share of gross absolute components | {100 * country_summary['usa_china_share_of_gross_absolute_components']:.1f}% |",
        f"| Mean after accounting leave-out of U.S. + China | {money(country_summary['leave_out_usa_and_china_global_mean_usd2020_per_tco2'])} |",
        "",
        "## Panel E. Signed present-value shares by period",
        "",
        "| GIVE schedule | 2020--2050 | 2051--2100 | 2101--2200 | 2201--2300 |",
        "|---:|---:|---:|---:|---:|",
    ])
    require(len(period_grid["results"]) == 4, "period-grid schedule support differs")
    for result in period_grid["results"]:
        shares = [100 * row["share_of_signed_total"] for row in result["periods"]]
        lines.append(
            f"| {result['discount_rate_label']} | {shares[0]:.1f}% | {shares[1]:.1f}% | "
            f"{shares[2]:.1f}% | {shares[3]:.1f}% |"
        )
    lines.extend([
        "",
        "The structural design crosses 26 climate models, three adaptation cases, two tail rules, three elasticity pairs, and two yield-to-supply mappings. Panel C instead holds adaptation and tail treatment fixed while propagating the shared published coefficient covariance separately through each market case. Panels D and E are accounting decompositions of the central narrow result, not alternative estimands. No panel includes omitted timing, drought, temperature, irrigation, crop-coverage, trade, or storage mechanisms.",
        "",
    ])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines))
    receipt = {
        "schema": "manuscript_scc_table/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "support": {"discount_schedules": 4, "adaptation_rows": 3, "market_rows": 6, "geographic_diagnostics": 4, "period_schedule_rows": 4},
        "claim_gates": {"paired_quantity_channel_scc": True, "probabilistic_total_uncertainty": False, "full_precipitation_agriculture_scc": False},
        "sources": {
            "structural": {"path": str(args.structural), "sha256": digest(args.structural)},
            "coefficient_grid": {"path": str(args.coefficient_grid), "sha256": digest(args.coefficient_grid)},
            "market_grid": {"path": str(args.market_grid), "sha256": digest(args.market_grid)},
            "country": {"path": str(args.country), "sha256": digest(args.country)},
            "period_grid": {"path": str(args.period_grid), "sha256": digest(args.period_grid)},
        },
        "output": {"path": str(args.output), "sha256": digest(args.output)},
        "implementation": {"path": str(Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1])), "sha256": digest(Path(__file__).resolve())},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", "support": receipt["support"], "output_sha256": receipt["output"]["sha256"]}, indent=2))


if __name__ == "__main__":
    main()

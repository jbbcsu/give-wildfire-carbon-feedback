#!/usr/bin/env python3
"""Render the validated national 990 m USDM result as a manuscript-ready note."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

TERMS = [f"d{level}_weeks" for level in range(5)]
TERM_LABELS = [f"D{level}" for level in range(5)]
BASIS_LABELS = {"county": "Whole county", "cultivated": "Cultivated 990 m", "broad": "Broad agriculture 990 m"}
CROP_LABELS = {"corn_grain": "Corn", "soybeans": "Soybean"}
IRRIGATION_LABELS = {"dryland": "Dryland", "irrigated": "Irrigated"}


def coefficient_rows(summary: dict, family: str) -> list[str]:
    lines = ["| Crop | Support | Basis | D0 | D1 | D2 | D3 | D4 |", "|---|---|---|---:|---:|---:|---:|---:|"]
    for basis in ("county", "cultivated", "broad"):
        rows = summary["bases"][basis][family]["coefficients"]
        indexed = {
            (row["outcome_crop"], row["irrigation_class"], row["term"]):
            row["exact_percent_change_per_equivalent_week"]
            for row in rows
        }
        for crop in ("corn_grain", "soybeans"):
            for irrigation in ("dryland", "irrigated"):
                values = [indexed[crop, irrigation, term] for term in TERMS]
                lines.append(
                    f"| {CROP_LABELS[crop]} | {IRRIGATION_LABELS[irrigation]} | {BASIS_LABELS[basis]} | "
                    + " | ".join(f"{value:+.4f}" for value in values) + " |"
                )
    return lines


def movement_rows(summary: dict, key: str) -> list[str]:
    lines = ["| Model | Comparison | Mean absolute movement | Maximum movement | Maximum term |", "|---|---|---:|---:|---|"]
    source = summary[key]
    for family in ("drought_only", "drought_plus_weather"):
        for comparison, values in source[family].items():
            maximum = values["maximum_absolute_movement"]
            term = "/".join(
                str(maximum[field])
                for field in ("outcome_crop", "irrigation_class", "term")
            )
            lines.append(
                f"| {family.replace('_', ' ')} | {comparison.replace('_', ' ')} | "
                f"{values['mean_absolute_movement_percentage_point_per_equivalent_week']:.5f} | "
                f"{maximum['absolute_movement_percentage_point_per_equivalent_week']:.5f} | {term} |"
            )
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--merged-validation", type=Path, required=True)
    parser.add_argument("--independent-validation", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    summary = json.loads(args.summary.read_text())
    merged = json.loads(args.merged_validation.read_text())
    independent = json.loads(args.independent_validation.read_text())
    if independent.get("status") != "passed":
        raise ValueError("independent validation did not pass")

    published = summary["published_table_2"]["means_equivalent_weeks"]
    exposure_lines = ["| Basis | County-years | Counties | D0 | D1 | D2 | D3 | D4 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    exposure_lines.append("| Published Table 2 | 40,040 | -- | " + " | ".join(f"{published[term]:.3f}" for term in TERMS) + " |")
    for basis in ("county", "cultivated", "broad"):
        exposure = summary["bases"][basis]["exposure"]
        exposure_lines.append(
            f"| {BASIS_LABELS[basis]} | {exposure['unique_county_years']:,} | {exposure['counties']:,} | "
            + " | ".join(f"{exposure['means_equivalent_weeks'][term]:.3f}" for term in TERMS) + " |"
        )

    robustness_lines = ["| Basis | Crop | Support | Category | Estimate | State-cluster p | Leave-one-state-out same-sign share |", "|---|---|---|---|---:|---:|---:|"]
    for basis in ("cultivated", "broad"):
        rows = summary["bases"][basis]["state_robustness"]["coefficients"]
        selected = [
            row for row in rows
            if row["p_value_state_t_reference"] < 0.05
            or row["same_nonzero_sign_fraction_leave_one_state_out"] == 1.0
        ]
        for row in selected:
            robustness_lines.append(
                f"| {BASIS_LABELS[basis]} | {CROP_LABELS[row['outcome_crop']]} | "
                f"{IRRIGATION_LABELS[row['irrigation_class']]} | {row['term'].split('_')[0].upper()} | "
                f"{row['exact_percent_change_per_equivalent_week']:+.4f} | "
                f"{row['p_value_state_t_reference']:.4f} | "
                f"{row['same_nonzero_sign_fraction_leave_one_state_out']:.3f} |"
            )
    if len(robustness_lines) == 2:
        robustness_lines.append("| -- | -- | -- | -- | -- | -- | No term met either reporting screen |")

    final_vs_rejected = summary.get("coefficient_movements_990m_vs_rejected_3_96km")
    rejected_section = []
    if final_vs_rejected:
        rejected_section = [
            "## Change from the rejected 3.96 km diagnostic",
            "",
            "The following movements compare the final-resolution coefficients with the previously rejected coarse diagnostic. They are fidelity diagnostics, not model-selection criteria.",
            "",
            *movement_rows(summary, "coefficient_movements_990m_vs_rejected_3_96km"),
            "",
        ]

    lines = [
        "# Final-resolution U.S. drought--yield agricultural-area results",
        "",
        "**Status:** completed historical U.S. sensitivity at 990 m with independent numerical and resource validation. This is not a causal yield response, future drought projection, global damage function, or SCC input.",
        "",
        "## Purpose",
        "",
        "This analysis replaces the rejected 3.96 km agricultural-area approximation with the predeclared national 990 m reconstruction, while holding the crop outcomes, irrigation classifier, fixed effects, direct-weather hierarchy, and inference procedures unchanged.",
        "",
        "## Construction and resource validation",
        "",
        f"The state-partitioned build covers {merged['state_count']} continental states, {merged['counties']:,} counties, two fixed CDL masks, and 13 harvest years. The merged exposure has {merged['rows']:,} county-mask-year rows. Maximum state grid and exposure RSS were {merged['maximum_grid_peak_rss_bytes'] / 2**20:.1f} MiB and {merged['maximum_exposure_peak_rss_bytes'] / 2**20:.1f} MiB, respectively, below the frozen 640 MiB ceiling. Annual mutually exclusive drought categories reconcile within {merged['maximum_category_sum_error_weeks']:.3g} week.",
        "",
        "## Exposure accounting",
        "",
        *exposure_lines,
        "",
        "Full-support mean differences combine spatial weighting and coverage. The summary separately reports exact common county-year support; neither mask is selected by proximity to the published means.",
        "",
        "## Historical drought-only associations",
        "",
        "Entries are exact fitted percent changes in yield for one additional area-equivalent week, conditional on the other mutually exclusive drought categories, county and year fixed effects, and state-specific trends.",
        "",
        *coefficient_rows(summary, "drought_only"),
        "",
        "## Direct-weather hierarchy",
        "",
        "These estimates additionally control for April--September rainfall, rainfall squared, mean temperature, and crop-threshold heat exposure. Composite drought and direct weather are treated as competing descriptions rather than additive damage channels.",
        "",
        *coefficient_rows(summary, "drought_plus_weather"),
        "",
        "## Spatial-basis movement within the final comparison",
        "",
        *movement_rows(summary, "coefficient_movements_within_final_comparison"),
        "",
        *rejected_section,
        "## State-cluster and leave-one-state-out screen",
        "",
        "The table reports every weather-controlled term that is either below 0.05 under state-cluster inference or retains the same nonzero sign in every represented-state deletion. This is a stability screen, not a multiple-testing-adjusted discovery rule.",
        "",
        *robustness_lines,
        "",
        "## Interpretation boundary",
        "",
        "The final 990 m reconstruction establishes the spatial fidelity of the historical U.S. drought benchmark and quantifies how much the coarse approximation moved its associations. It does not identify a causal USDM response, project future drought, establish transferability outside the United States, monetize damages, or authorize any SCC calculation. Those gates remain false in both the summary and independent validation receipts.",
        "",
        "Machine-readable sources:",
        "",
        f"- `{args.summary}`",
        f"- `{args.merged_validation}`",
        f"- `{args.independent_validation}`",
        "",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()

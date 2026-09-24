#!/usr/bin/env python3
"""Plot the validated five-ESM maize precipitation-response decomposition."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

COMPONENTS = [
    ("precipitation_all_income_support", "Net precipitation"),
    ("precipitation_quantity_reference_scaling", "Quantity path"),
    ("precipitation_distribution_residual", "Timing / distribution"),
]
MODEL_LABELS = {
    "GFDL-ESM4": "GFDL",
    "IPSL-CM6A-LR": "IPSL",
    "MPI-ESM1-2-HR": "MPI",
    "MRI-ESM2-0": "MRI",
    "UKESM1-0-LL": "UKESM",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--svg", type=Path, required=True)
    args = parser.parse_args()

    record = json.loads(args.input.read_text(encoding="utf-8"))
    require(record["status"] == "named_model_transport_summary_not_probability_damage_or_scc", "input status failed")
    require(len(record["climate_models"]) == 5, "five named ESMs required")
    full = record["support_sensitivities"]["full"]["fixed"]
    weighting = record.get("analysis_weighting", {"label": "fixed MIRCA harvested area", "unit": "ha"})
    models = record["climate_models"]
    require(set(models) == set(MODEL_LABELS), "model set differs")

    values: list[list[float]] = []
    for key, _ in COMPONENTS:
        rows = {row["climate_model"]: row for row in full[key]["named_model_results"]}
        values.append([rows[model]["percent_change_from_mean_log"] for model in models])
    width, height = 900, 520
    left, right, top, bottom = 80, 30, 70, 90
    plot_width, plot_height = width - left - right, height - top - bottom
    y_min, y_max = -6.0, 2.0
    y = lambda value: top + (y_max - value) / (y_max - y_min) * plot_height
    group_width = plot_width / len(models)
    bar_width = 34
    colors = ["#34495e", "#d35400", "#2e86c1"]
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#222}.small{font-size:12px}.tick{font-size:13px}.title{font-size:18px;font-weight:600}</style>',
        f'<text x="{width/2}" y="28" text-anchor="middle" class="title">Published maize response to SSP5-8.5 minus SSP1-2.6 weather, 2092–2100</text>',
        f'<text x="{width/2}" y="49" text-anchor="middle" class="small" fill="#555">{html.escape(weighting["label"])}; coefficient transport, not damage or SCC</text>',
    ]
    for tick in range(-6, 3, 2):
        yy = y(float(tick))
        svg.append(f'<line x1="{left}" x2="{width-right}" y1="{yy:.2f}" y2="{yy:.2f}" stroke="#dddddd" stroke-width="1"/>')
        svg.append(f'<text x="{left-10}" y="{yy+4:.2f}" text-anchor="end" class="tick">{tick}</text>')
    zero_y = y(0.0)
    svg.append(f'<line x1="{left}" x2="{width-right}" y1="{zero_y:.2f}" y2="{zero_y:.2f}" stroke="#111" stroke-width="1.3"/>')
    for model_index, model in enumerate(models):
        center = left + (model_index + 0.5) * group_width
        svg.append(f'<text x="{center:.2f}" y="{height-bottom+28}" text-anchor="middle" class="tick">{html.escape(MODEL_LABELS[model])}</text>')
        for component_index, color in enumerate(colors):
            value = values[component_index][model_index]
            x = center + (component_index - 1) * (bar_width + 5) - bar_width / 2
            yy = y(value)
            rect_y, rect_height = min(yy, zero_y), abs(yy - zero_y)
            svg.append(f'<rect x="{x:.2f}" y="{rect_y:.2f}" width="{bar_width}" height="{rect_height:.2f}" fill="{color}"/>')
    axis_label = "Production-weighted mean yield change (%)" if weighting["unit"] == "mt" else "Area-weighted mean yield change (%)"
    svg.append(f'<text transform="translate(20 {top + plot_height/2}) rotate(-90)" text-anchor="middle" class="tick">{axis_label}</text>')
    legend_y = height - 25
    for index, ((_, label), color) in enumerate(zip(COMPONENTS, colors, strict=True)):
        x = 180 + index * 235
        svg.append(f'<rect x="{x}" y="{legend_y-11}" width="14" height="14" fill="{color}"/>')
        svg.append(f'<text x="{x+21}" y="{legend_y}" class="small">{html.escape(label)}</text>')
    svg.append('</svg>')
    args.svg.parent.mkdir(parents=True, exist_ok=True)
    args.svg.write_text("\n".join(svg) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

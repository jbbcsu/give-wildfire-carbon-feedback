#!/usr/bin/env python3
"""Create a dependency-free SVG of model-specific coefficient intervals."""

from __future__ import annotations

import argparse
import hashlib
import html
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh output and receipt required")
    source = json.loads(args.input.read_text())
    require(source["schema"] == "quantity_coefficient_delta_by_model/v1", "input schema differs")
    rows = [row for row in source["rows"] if row["discount_rate_label"] == "2.0%"]
    require(len(rows) == 26 and len({row["climate_model"] for row in rows}) == 26, "2% support differs")
    summary = next(row for row in source["summaries"] if row["discount_rate_label"] == "2.0%")
    mean = summary["central_equal_model_mean_usd2020_per_tco2"]
    mean_se = summary["shared_coefficient_delta_se_of_equal_model_mean_usd2020_per_tco2"]

    def category(row: dict) -> str:
        if row["normal_approximation_95_upper_usd2020_per_tco2"] < 0:
            return "below"
        if row["normal_approximation_95_lower_usd2020_per_tco2"] > 0:
            return "above"
        return "includes"

    rows.sort(key=lambda row: row["central_scc_usd2020_per_tco2"], reverse=True)
    counts = {key: sum(category(row) == key for row in rows) for key in ("below", "includes", "above")}
    require(counts == {"below": 23, "includes": 2, "above": 1}, "interval classification differs")

    width, height = 1000, 1160
    left, right, top, bottom = 275, 955, 125, 1015
    x_min, x_max = -0.020, 0.007
    ticks = [-0.020, -0.015, -0.010, -0.005, 0.000, 0.005]
    colors = {"below": "#2166AC", "includes": "#777777", "above": "#B35806", "mean": "#111111"}

    def xpos(value: float) -> float:
        return left + (value - x_min) / (x_max - x_min) * (right - left)

    row_gap = (bottom - top - 55) / len(rows)
    svg = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;fill:#222}.title{font-size:24px;font-weight:700}.subtitle{font-size:15px;fill:#444}.label{font-size:13px}.tick{font-size:12px;fill:#555}.caption{font-size:12px;fill:#444}.legend{font-size:12px}</style>',
        '<text x="40" y="42" class="title">Annual-maize rainfall-quantity SCC by climate model</text>',
        '<text x="40" y="68" class="subtitle">Central fixed-adaptation, uncapped specification; GIVE 2% Ramsey schedule</text>',
    ]
    for tick in ticks:
        x = xpos(tick)
        stroke = "#555555" if tick == 0 else "#E5E5E5"
        stroke_width = 1.5 if tick == 0 else 1
        svg.append(f'<line x1="{x:.2f}" y1="{top-15}" x2="{x:.2f}" y2="{bottom}" stroke="{stroke}" stroke-width="{stroke_width}"/>')
        svg.append(f'<text x="{x:.2f}" y="{bottom+24}" text-anchor="middle" class="tick">{tick:.3f}</text>')

    for index, row in enumerate(rows):
        y = top + index * row_gap
        group = category(row)
        color = colors[group]
        low = xpos(row["normal_approximation_95_lower_usd2020_per_tco2"])
        high = xpos(row["normal_approximation_95_upper_usd2020_per_tco2"])
        point = xpos(row["central_scc_usd2020_per_tco2"])
        label = html.escape(row["climate_model"])
        svg.extend([
            f'<text x="{left-14}" y="{y+4:.2f}" text-anchor="end" class="label">{label}</text>',
            f'<line x1="{low:.2f}" y1="{y:.2f}" x2="{high:.2f}" y2="{y:.2f}" stroke="{color}" stroke-width="3"/>',
            f'<line x1="{low:.2f}" y1="{y-4:.2f}" x2="{low:.2f}" y2="{y+4:.2f}" stroke="{color}" stroke-width="2"/>',
            f'<line x1="{high:.2f}" y1="{y-4:.2f}" x2="{high:.2f}" y2="{y+4:.2f}" stroke="{color}" stroke-width="2"/>',
            f'<circle cx="{point:.2f}" cy="{y:.2f}" r="4.5" fill="{color}"/>',
        ])

    mean_y = bottom - 5
    mean_low, mean_high = xpos(mean - 1.96 * mean_se), xpos(mean + 1.96 * mean_se)
    mean_x = xpos(mean)
    svg.extend([
        f'<line x1="{left-240}" y1="{mean_y-19}" x2="{right}" y2="{mean_y-19}" stroke="#BBBBBB" stroke-width="1"/>',
        f'<text x="{left-14}" y="{mean_y+4}" text-anchor="end" class="label" font-weight="700">Equal-model mean</text>',
        f'<line x1="{mean_low:.2f}" y1="{mean_y}" x2="{mean_high:.2f}" y2="{mean_y}" stroke="{colors["mean"]}" stroke-width="3"/>',
        f'<polygon points="{mean_x:.2f},{mean_y-6} {mean_x+6:.2f},{mean_y} {mean_x:.2f},{mean_y+6} {mean_x-6:.2f},{mean_y}" fill="{colors["mean"]}"/>',
        f'<text x="{(left+right)/2:.2f}" y="{bottom+55}" text-anchor="middle" class="subtitle">2020 USD per tCO₂ (negative = modeled benefit)</text>',
    ])
    legend_y = 1092
    legend = [("below", "Interval below zero"), ("includes", "Interval includes zero"), ("above", "Interval above zero"), ("mean", "Equal-model mean")]
    positions = [90, 310, 535, 750]
    for x, (key, label) in zip(positions, legend):
        svg.append(f'<circle cx="{x}" cy="{legend_y}" r="5" fill="{colors[key]}"/>')
        svg.append(f'<text x="{x+12}" y="{legend_y+4}" class="legend">{label}</text>')
    svg.extend([
        '<text x="40" y="1130" class="caption">Bars are first-order normal intervals from the published coefficient covariance only.</text>',
        '<text x="40" y="1148" class="caption">Climate-model spread is descriptive, not a probability distribution.</text>',
        '</svg>',
    ])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(svg) + "\n")

    receipt = {
        "schema": "quantity_coefficient_interval_figure/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "estimand": "central fixed-adaptation uncapped annual-maize rainfall-quantity SCC at the 2% GIVE schedule",
        "support": {"climate_models": len(rows), "coefficient_interval_counts": counts, "includes_equal_model_mean": True},
        "interpretation": {
            "coefficient_intervals": "first-order normal intervals conditional on each climate model and the narrow quantity channel",
            "climate_models": "named unweighted models; not probability draws",
        },
        "sources": {"input": {"path": str(args.input), "sha256": digest(args.input)}},
        "output": {"path": str(args.output), "sha256": digest(args.output)},
        "implementation": {"path": str(Path(__file__).relative_to(Path(__file__).parents[1])), "sha256": digest(Path(__file__))},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", "counts": counts, "output_sha256": receipt["output"]["sha256"]}, indent=2))


if __name__ == "__main__":
    main()

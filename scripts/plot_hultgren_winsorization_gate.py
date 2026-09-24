#!/usr/bin/env python3
"""Plot raw and published-style winsorized fixed-price output exposures."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

LABELS = {"GFDL-ESM4": "GFDL", "IPSL-CM6A-LR": "IPSL", "MPI-ESM1-2-HR": "MPI", "MRI-ESM2-0": "MRI", "UKESM1-0-LL": "UKESM"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--svg", type=Path, required=True)
    args = parser.parse_args()
    result = json.loads(args.input.read_text(encoding="utf-8"))
    if result["status"] != "published_style_tail_sensitivity_not_exact_replication_welfare_damage_or_scc":
        raise ValueError("input status differs")
    models = list(LABELS)
    raw = [result["by_climate_model"][model]["raw_weighted_mean_cell_exact_percent"] for model in models]
    capped = [result["by_climate_model"][model]["winsorized_weighted_mean_cell_exact_percent"] for model in models]
    width, height = 900, 520
    left, right, top, bottom = 80, 30, 70, 90
    plot_width, plot_height = width - left - right, height - top - bottom
    y_min, y_max = -5.0, 22.0
    y = lambda value: top + (y_max - value) / (y_max - y_min) * plot_height
    group_width, bar_width = plot_width / len(models), 46
    zero = y(0.0)
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#222}.small{font-size:12px}.tick{font-size:13px}.title{font-size:18px;font-weight:600}</style>',
        f'<text x="{width/2}" y="28" text-anchor="middle" class="title">Tail behavior blocks direct monetization without a response rule</text>',
        f'<text x="{width/2}" y="49" text-anchor="middle" class="small">Value-weighted cell-first precipitation response; fixed prices, not welfare damage or SCC</text>',
    ]
    for tick in (-5, 0, 5, 10, 15, 20):
        yy = y(float(tick))
        svg.append(f'<line x1="{left}" x2="{width-right}" y1="{yy:.2f}" y2="{yy:.2f}" stroke="#dddddd"/>')
        svg.append(f'<text x="{left-10}" y="{yy+4:.2f}" text-anchor="end" class="tick">{tick}</text>')
    svg.append(f'<line x1="{left}" x2="{width-right}" y1="{zero:.2f}" y2="{zero:.2f}" stroke="#111" stroke-width="1.3"/>')
    for index, model in enumerate(models):
        center = left + (index + 0.5) * group_width
        svg.append(f'<text x="{center:.2f}" y="{height-bottom+28}" text-anchor="middle" class="tick">{html.escape(LABELS[model])}</text>')
        for offset, value, color in ((-1, raw[index], "#b7bcc2"), (0, capped[index], "#2e86c1")):
            x = center + (offset + 0.5) * (bar_width + 7) - bar_width / 2
            yy = y(value)
            svg.append(f'<rect x="{x:.2f}" y="{min(yy, zero):.2f}" width="{bar_width}" height="{abs(yy-zero):.2f}" fill="{color}"/>')
    svg.append(f'<text transform="translate(20 {top+plot_height/2}) rotate(-90)" text-anchor="middle" class="tick">Aggregate fixed-price output change (%)</text>')
    for x, color, label in ((280, "#b7bcc2", "Unrestricted"), (500, "#2e86c1", "Published-style 1% winsorization")):
        svg.append(f'<rect x="{x}" y="{height-36}" width="14" height="14" fill="{color}"/>')
        svg.append(f'<text x="{x+21}" y="{height-25}" class="small">{label}</text>')
    svg.append('</svg>')
    args.svg.parent.mkdir(parents=True, exist_ok=True)
    args.svg.write_text("\n".join(svg) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

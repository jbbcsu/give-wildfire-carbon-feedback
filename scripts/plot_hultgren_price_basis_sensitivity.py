#!/usr/bin/env python3
"""Plot central fixed national-market results as dependency-free SVG."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

MODELS = ["GFDL-ESM4", "IPSL-CM6A-LR", "MPI-ESM1-2-HR", "MRI-ESM2-0", "UKESM1-0-LL"]


def central(path: Path) -> dict[str, float]:
    result = json.loads(path.read_text(encoding="utf-8"))
    cases = [case for case in result["scenarios"]["fixed"]["cases"]
             if case["central_elasticity"] and case["yield_to_supply_mapping"] == "horizontal_output"]
    values = {case["climate_model"]: case["mean_annual_damage_change"] / 1e9 for case in cases}
    if result["schema"] != "hultgren_country_maize_market_sensitivity/v1" or set(values) != set(MODELS):
        raise ValueError("market schema or model support differs")
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--constant", type=Path, required=True)
    parser.add_argument("--rebased", type=Path, required=True)
    parser.add_argument("--common", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.suffix.lower() != ".svg":
        raise ValueError("output must be SVG")
    constant, rebased, common = central(args.constant), central(args.rebased), central(args.common)
    labels = ["GFDL", "IPSL", "MPI", "MRI", "UKESM", "5-model mean"]
    first = [constant[model] for model in MODELS]
    second = [rebased[model] for model in MODELS]
    third = [common[model] for model in MODELS]
    first.append(sum(first) / 5.0); second.append(sum(second) / 5.0); third.append(sum(third) / 5.0)

    width, height = 1000, 580
    left, right, top, bottom = 105, 35, 145, 105
    plot_w, plot_h = width - left - right, height - top - bottom
    ymax = 10.0
    y = lambda value: top + plot_h * (1.0 - value / ymax)
    group, bar_w = plot_w / len(labels), 26
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;fill:#222}.title{font-size:22px;font-weight:600}.sub{font-size:13px;fill:#555}.axis{font-size:12px;fill:#444}.value{font-size:12px;font-weight:600}</style>',
        f'<text x="{width/2}" y="32" text-anchor="middle" class="title">National maize-market magnitude depends on the baseline price basis</text>',
        f'<text x="{width/2}" y="56" text-anchor="middle" class="sub">Central fixed-adaptation structural sensitivity; not GIVE damage or SCC</text>',
        '<rect x="515" y="68" width="15" height="15" fill="#9b6b43"/><text x="538" y="80" class="axis">FAOSTAT constant-dollar field (flagged)</text>',
        '<rect x="515" y="90" width="15" height="15" fill="#2878a5"/><text x="538" y="102" class="axis">Current USD, GDP-deflator rebased</text>',
        '<rect x="515" y="112" width="15" height="15" fill="#4b8b3b"/><text x="538" y="124" class="axis">Same total value, common maize price</text>',
    ]
    for tick in range(0, 11, 2):
        yy = y(float(tick))
        parts.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}" stroke="#dedede"/>')
        parts.append(f'<text x="{left-12}" y="{yy+4:.1f}" text-anchor="end" class="axis">{tick}</text>')
    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" stroke="#444"/>')
    parts.append(f'<line x1="{left}" y1="{top+plot_h}" x2="{width-right}" y2="{top+plot_h}" stroke="#444"/>')
    for index, label in enumerate(labels):
        center = left + group * (index + 0.5)
        for offset, value, color in [(-1.5 * bar_w, first[index], "#9b6b43"), (-0.5 * bar_w, second[index], "#2878a5"), (0.5 * bar_w, third[index], "#4b8b3b")]:
            xx, yy = center + offset, y(value)
            parts.append(f'<rect x="{xx:.1f}" y="{yy:.1f}" width="{bar_w}" height="{top+plot_h-yy:.1f}" fill="{color}"/>')
            parts.append(f'<text x="{xx+bar_w/2:.1f}" y="{yy-7:.1f}" text-anchor="middle" class="value">{value:.2f}</text>')
        parts.append(f'<text x="{center:.1f}" y="{top+plot_h+26}" text-anchor="middle" class="axis">{html.escape(label)}</text>')
    parts += [
        f'<text x="25" y="{top+plot_h/2}" text-anchor="middle" class="axis" transform="rotate(-90 25 {top+plot_h/2})">Mean annual damage-signed surplus change (billion 2014–2016-basis US dollars)</text>',
        '</svg>',
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(parts) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

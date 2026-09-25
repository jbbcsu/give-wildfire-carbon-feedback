#!/usr/bin/env python3
"""Create an SVG of temporal SCC shares across GIVE discount schedules."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh outputs required")
    source = json.loads(args.input.read_text())
    require(source["schema"] == "quantity_scc_period_discount_grid/v1", "input schema differs")
    rows = source["results"]
    require([row["discount_rate_label"] for row in rows] == ["1.5%", "2.0%", "2.5%", "3.0%"], "schedule order differs")
    require(all(len(row["periods"]) == 4 for row in rows), "period support differs")

    width, height = 1040, 570
    left, right, top = 200, 970, 145
    bar_height, gap = 54, 42
    colors = ["#2166AC", "#67A9CF", "#D1E5F0", "#F4A582"]
    period_labels = ["2020–2050", "2051–2100", "2101–2200", "2201–2300"]

    def xpos(share: float) -> float:
        return left + share * (right - left)

    svg = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;fill:#222}.title{font-size:24px;font-weight:700}.subtitle{font-size:15px;fill:#444}.row{font-size:16px;font-weight:600}.inside{font-size:12px;font-weight:600}.tick{font-size:12px;fill:#555}.legend{font-size:12px}.caption{font-size:12px;fill:#444}</style>',
        '<text x="38" y="42" class="title">When the rainfall-quantity SCC accrues</text>',
        '<text x="38" y="70" class="subtitle">Signed present-value shares by GIVE Ramsey discount schedule</text>',
    ]
    for tick in (0.0, 0.25, 0.5, 0.75, 1.0):
        x = xpos(tick)
        svg.append(f'<line x1="{x:.2f}" y1="{top-22}" x2="{x:.2f}" y2="{top+4*(bar_height+gap)-gap+8}" stroke="#E5E5E5" stroke-width="1"/>')
        svg.append(f'<text x="{x:.2f}" y="{top-34}" text-anchor="middle" class="tick">{int(tick*100)}%</text>')
    for index, row in enumerate(rows):
        y = top + index * (bar_height + gap)
        svg.append(f'<text x="{left-18}" y="{y+23}" text-anchor="end" class="row">{row["discount_rate_label"]}</text>')
        svg.append(f'<text x="{left-18}" y="{y+42}" text-anchor="end" class="tick">${row["equal_model_mean_usd2020_per_tco2"]:.5f}/tCO₂</text>')
        cumulative = 0.0
        for period_index, (color, period) in enumerate(zip(colors, row["periods"])):
            share = float(period["share_of_signed_total"])
            start, end = xpos(cumulative), xpos(cumulative + share)
            svg.append(f'<rect x="{start:.2f}" y="{y}" width="{end-start:.2f}" height="{bar_height}" fill="{color}" stroke="white" stroke-width="1"/>')
            if share >= 0.07:
                label_color = "white" if period_index == 0 else "#222"
                svg.append(f'<text x="{(start+end)/2:.2f}" y="{y+32}" text-anchor="middle" class="inside" fill="{label_color}">{share*100:.1f}%</text>')
            cumulative += share
        require(abs(cumulative - 1.0) <= 1e-12, "period shares differ from one")
    legend_y = 505
    for index, (color, label) in enumerate(zip(colors, period_labels)):
        x = 175 + index * 205
        svg.append(f'<rect x="{x}" y="{legend_y-11}" width="16" height="16" fill="{color}"/>')
        svg.append(f'<text x="{x+23}" y="{legend_y+2}" class="legend">{label}</text>')
    svg.extend(
        [
            '<text x="38" y="550" class="caption">Shares sum to each schedule’s signed narrow-channel SCC; schedules reweight one physical path and are not probability draws.</text>',
            '</svg>',
        ]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(svg) + "\n")
    receipt = {
        "schema": "quantity_scc_period_discount_figure/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "support": {"discount_schedules": 4, "periods_per_schedule": 4},
        "interpretation": "signed present-value timing shares of the narrow annual-maize rainfall-quantity SCC",
        "sources": {"input": {"path": str(args.input), "sha256": digest(args.input)}},
        "output": {"path": str(args.output), "sha256": digest(args.output)},
        "implementation": {
            "path": str(Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1])),
            "sha256": digest(Path(__file__).resolve()),
        },
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", "support": receipt["support"], "output_sha256": receipt["output"]["sha256"]}, indent=2))


if __name__ == "__main__":
    main()

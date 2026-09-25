#!/usr/bin/env python3
"""Create an SVG of leading country components in the narrow quantity SCC."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


NAMES = {
    "ARG": "Argentina",
    "BRA": "Brazil",
    "CAN": "Canada",
    "CHN": "China",
    "ETH": "Ethiopia",
    "IND": "India",
    "KEN": "Kenya",
    "MEX": "Mexico",
    "THA": "Thailand",
    "TZA": "Tanzania",
    "USA": "United States",
    "ZAF": "South Africa",
}


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
    parser.add_argument("input_receipt", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    require(not args.output.exists() and not args.receipt.exists(), "fresh output and receipt required")
    source = json.loads(args.input_receipt.read_text())
    require(source["schema"] == "quantity_scc_country_decomposition/v1", "input schema differs")
    table = Path(source["output"]["path"])
    require(table.is_file() and digest(table) == source["output"]["sha256"], "country table differs")
    frame = pd.read_csv(table)
    require(len(frame) == 106, "country support differs")
    frame["absolute_mean"] = frame.equal_model_mean_usd2020_per_tco2.abs()
    rows = frame.nlargest(12, "absolute_mean").copy()
    require(set(rows.iso3) == set(NAMES), "leading-country set differs")
    rows = rows.sort_values("equal_model_mean_usd2020_per_tco2", ascending=False).reset_index(drop=True)

    width, height = 1020, 700
    left, right, top, bottom = 245, 970, 125, 565
    x_min, x_max = -0.0062, 0.0031
    ticks = [-0.006, -0.004, -0.002, 0.000, 0.002]
    benefit, damage = "#2166AC", "#B35806"

    def xpos(value: float) -> float:
        return left + (value - x_min) / (x_max - x_min) * (right - left)

    gap = (bottom - top) / (len(rows) - 1)
    svg = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;fill:#222}.title{font-size:24px;font-weight:700}.subtitle{font-size:15px;fill:#444}.label{font-size:14px}.tick{font-size:12px;fill:#555}.caption{font-size:12px;fill:#444}.legend{font-size:13px}</style>',
        '<text x="38" y="42" class="title">Country accounting components of the rainfall-quantity SCC</text>',
        '<text x="38" y="69" class="subtitle">Twelve largest absolute equal-model means; bars span 26 climate models</text>',
    ]
    for tick in ticks:
        x = xpos(tick)
        stroke = "#555555" if tick == 0 else "#E5E5E5"
        line_width = 1.6 if tick == 0 else 1
        svg.append(f'<line x1="{x:.2f}" y1="{top-18}" x2="{x:.2f}" y2="{bottom+10}" stroke="{stroke}" stroke-width="{line_width}"/>')
        svg.append(f'<text x="{x:.2f}" y="{bottom+36}" text-anchor="middle" class="tick">{tick:+.3f}</text>')
    for index, row in rows.iterrows():
        y = top + index * gap
        mean = float(row.equal_model_mean_usd2020_per_tco2)
        color = benefit if mean < 0 else damage
        low = xpos(float(row.climate_model_min_usd2020_per_tco2))
        high = xpos(float(row.climate_model_max_usd2020_per_tco2))
        point = xpos(mean)
        name = html.escape(NAMES[str(row.iso3)])
        svg.extend(
            [
                f'<text x="{left-16}" y="{y+5:.2f}" text-anchor="end" class="label">{name}</text>',
                f'<line x1="{low:.2f}" y1="{y:.2f}" x2="{high:.2f}" y2="{y:.2f}" stroke="#888" stroke-width="2.5"/>',
                f'<line x1="{low:.2f}" y1="{y-4:.2f}" x2="{low:.2f}" y2="{y+4:.2f}" stroke="#888" stroke-width="2"/>',
                f'<line x1="{high:.2f}" y1="{y-4:.2f}" x2="{high:.2f}" y2="{y+4:.2f}" stroke="#888" stroke-width="2"/>',
                f'<circle cx="{point:.2f}" cy="{y:.2f}" r="5.5" fill="{color}" stroke="white" stroke-width="1"/>',
            ]
        )
    legend_y = 630
    svg.extend(
        [
            f'<circle cx="185" cy="{legend_y}" r="6" fill="{benefit}"/><text x="199" y="{legend_y+5}" class="legend">Negative component (modeled benefit)</text>',
            f'<circle cx="515" cy="{legend_y}" r="6" fill="{damage}"/><text x="529" y="{legend_y+5}" class="legend">Positive component (modeled damage)</text>',
            '<text x="38" y="674" class="caption">Accounting decomposition of the central fixed-adaptation, uncapped 2% case; not country causal effects.</text>',
            '</svg>',
        ]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(svg) + "\n")
    receipt = {
        "schema": "quantity_scc_country_decomposition_figure/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "support": {"countries_total": len(frame), "countries_plotted": len(rows), "climate_models": 26},
        "interpretation": "country accounting components of the narrow quantity channel; not local causal effects",
        "sources": {
            "decomposition_receipt": {"path": str(args.input_receipt), "sha256": digest(args.input_receipt)},
            "country_table": {"path": str(table), "sha256": digest(table)},
        },
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

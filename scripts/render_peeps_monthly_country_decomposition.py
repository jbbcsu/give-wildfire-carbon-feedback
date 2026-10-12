#!/usr/bin/env python3
"""Render country and FUND-region SCC components as a dependency-free SVG."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def svg_text(x: float, y: float, value: str, size: int = 12, anchor: str = "start", weight: str = "normal", fill: str = "#222222") -> str:
    return f'<text x="{x:.1f}" y="{y:.1f}" font-family="Arial,Helvetica,sans-serif" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{fill}">{html.escape(value)}</text>'


def draw_panel(frame: pd.DataFrame, label: str, title: str, x: float, y: float, width: float, height: float) -> list[str]:
    label_width = 142.0
    plot_x, plot_width = x + label_width, width - label_width - 14
    maximum = float(np.max(np.abs(frame[["joint_monthly_pattern", "quantity_reference"]].to_numpy()))) * 1.12
    maximum = max(maximum, 1e-9)
    zero = plot_x + plot_width / 2
    scale = plot_width / (2 * maximum)
    top, bottom = y + 42, y + height - 48
    row_height = (bottom - top) / len(frame)
    lines = [svg_text(x, y + 17, title, 15, weight="bold")]
    for tick in np.linspace(-maximum, maximum, 5):
        tx = zero + tick * scale
        lines.append(f'<line x1="{tx:.1f}" y1="{top - 8:.1f}" x2="{tx:.1f}" y2="{bottom + 4:.1f}" stroke="#dedede" stroke-width="1"/>')
        lines.append(svg_text(tx, bottom + 21, f"{tick:+.3f}" if abs(tick) >= 0.0005 else "0", 10, anchor="middle", fill="#555555"))
    lines.append(f'<line x1="{zero:.1f}" y1="{top - 8:.1f}" x2="{zero:.1f}" y2="{bottom + 4:.1f}" stroke="#555555" stroke-width="1.2"/>')
    for row_index, row in enumerate(frame.itertuples(index=False)):
        center = top + (row_index + 0.5) * row_height
        name = str(getattr(row, label))
        quantity, timing, joint = float(row.quantity_reference), float(row.timing_increment), float(row.joint_monthly_pattern)
        qx, jx = zero + quantity * scale, zero + joint * scale
        bar_height = min(16.0, row_height * 0.64)
        lines.append(svg_text(plot_x - 8, center + 4, name, 10, anchor="end"))
        lines.append(f'<rect x="{min(zero, qx):.1f}" y="{center - bar_height / 2:.1f}" width="{max(abs(qx - zero), 0.5):.1f}" height="{bar_height:.1f}" fill="#377eb8"/>')
        lines.append(f'<rect x="{min(qx, jx):.1f}" y="{center - bar_height / 2:.1f}" width="{max(abs(jx - qx), 0.5):.1f}" height="{bar_height:.1f}" fill="#f0a35e"/>')
        diamond = f"{jx:.1f},{center - 4:.1f} {jx + 4:.1f},{center:.1f} {jx:.1f},{center + 4:.1f} {jx - 4:.1f},{center:.1f}"
        lines.append(f'<polygon points="{diamond}" fill="#1b1b1b"/>')
    lines.append(svg_text(plot_x + plot_width / 2, y + height - 5, "2020 USD per tCO₂", 11, anchor="middle"))
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--country", type=Path, required=True)
    parser.add_argument("--region", type=Path, required=True)
    parser.add_argument("--source-receipt", type=Path, required=True)
    parser.add_argument("--svg", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.svg.exists() and not args.receipt.exists(), "fresh outputs required")
    source = json.loads(args.source_receipt.read_text())
    require(source["schema"] == "peeps_monthly_scc_country_decomposition/v1", "source receipt differs")
    require(source["outputs"]["country"]["sha256"] == digest(args.country), "country table hash differs")
    require(source["outputs"]["region"]["sha256"] == digest(args.region), "region table hash differs")
    filters = {"pulse_size_gtc": 0.000025, "adaptation": "fixed", "discount_rate_label": "2.0%"}
    country, region = pd.read_csv(args.country), pd.read_csv(args.region)
    for column, value in filters.items():
        country, region = country.loc[country[column].eq(value)], region.loc[region[column].eq(value)]
    country = country.pivot(index=["iso3", "country"], columns="channel", values="partial_scc_component_usd2020_per_tco2").reset_index()
    region = region.pivot(index="fund_region", columns="channel", values="partial_scc_component_usd2020_per_tco2").reset_index()
    require(len(country) == 107 and not country.isna().any().any(), "country figure support differs")
    require(len(region) == 17 and not region.isna().any().any(), "region figure support differs")
    selected_country = pd.concat([country.nsmallest(7, "joint_monthly_pattern"), country.nlargest(7, "joint_monthly_pattern")]).drop_duplicates("iso3").sort_values("joint_monthly_pattern").reset_index(drop=True)
    selected_region = region.loc[~region.fund_region.eq("UNMAPPED")].sort_values("joint_monthly_pattern").reset_index(drop=True)

    width, height = 1240, 700
    elements = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="white"/>']
    elements.append(svg_text(width / 2, 30, "The small global precipitation diagnostic masks large geographic offsets", 19, anchor="middle", weight="bold"))
    legend_y = 55
    elements.extend([f'<rect x="410" y="{legend_y - 10}" width="16" height="12" fill="#377eb8"/>', svg_text(433, legend_y, "Quantity reference", 11), f'<rect x="555" y="{legend_y - 10}" width="16" height="12" fill="#f0a35e"/>', svg_text(578, legend_y, "Timing increment", 11), f'<polygon points="700,{legend_y - 8} 705,{legend_y - 3} 700,{legend_y + 2} 695,{legend_y - 3}" fill="#1b1b1b"/>', svg_text(713, legend_y, "Joint total", 11)])
    elements.extend(draw_panel(selected_country, "country", "a  Largest country components", 22, 74, 588, 565))
    elements.extend(draw_panel(selected_region, "fund_region", "b  FUND-region components", 630, 74, 588, 565))
    elements.append(svg_text(width / 2, 671, "Fixed adaptation; smallest pulse; 2% schedule. One ESM/scenario and maize only. Accounting contributions, not local causal effects.", 10, anchor="middle", fill="#444444"))
    elements.append("</svg>")
    args.svg.parent.mkdir(parents=True, exist_ok=True)
    args.svg.write_text("\n".join(elements) + "\n")
    result = {"schema": "peeps_monthly_country_decomposition_figure/v1", "created_at_utc": datetime.now(timezone.utc).isoformat(), "status": "rendered_from_validated_accounting_decomposition", "filters": filters, "source": {"receipt": str(args.source_receipt), "receipt_sha256": digest(args.source_receipt), "country": {"path": str(args.country), "sha256": digest(args.country)}, "region": {"path": str(args.region), "sha256": digest(args.region)}}, "support": {"country_total": len(country), "country_displayed": len(selected_country), "region_total_including_unmapped": len(region), "region_displayed": len(selected_region)}, "output": {"path": str(args.svg), "bytes": args.svg.stat().st_size, "sha256": digest(args.svg)}, "claim_boundary": "visual accounting decomposition of one-ESM maize diagnostic; not local causal effects, total country damages, or paired-replacement SCC", "implementation": {"path": str(Path(__file__).resolve()), "sha256": digest(Path(__file__).resolve())}}
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

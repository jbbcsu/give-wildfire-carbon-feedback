#!/usr/bin/env python3
"""Audit country/FUND-region cancellation in the validated PEEPS SCC diagnostic."""
from __future__ import annotations

import argparse
import hashlib
import json
import resource
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


VALUE = "partial_scc_component_usd2020_per_tco2"
KEYS = ["pulse_size_gtc", "adaptation", "discount_rate_label", "channel"]
CHANNELS = ["joint_monthly_pattern", "quantity_reference", "timing_increment"]


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


def signed_metrics(values: np.ndarray) -> dict[str, Any]:
    values = np.asarray(values, dtype=float)
    require(len(values) > 0 and np.isfinite(values).all(), "signed metric input is empty or nonfinite")
    positive = float(values[values > 0].sum())
    negative = float(values[values < 0].sum())
    negative_magnitude = abs(negative)
    gross_absolute = positive + negative_magnitude
    net = float(values.sum())
    require(gross_absolute > 0, "gross absolute component is zero")
    dominant = max(positive, negative_magnitude)
    smaller = min(positive, negative_magnitude)
    return {
        "net": net,
        "gross_positive": positive,
        "gross_negative": negative,
        "gross_absolute": gross_absolute,
        "positive_count": int(np.sum(values > 0)),
        "negative_count": int(np.sum(values < 0)),
        "zero_count": int(np.sum(values == 0)),
        "absolute_net_share_of_gross_absolute": abs(net) / gross_absolute,
        "cancellation_fraction_of_gross_absolute": 1.0 - abs(net) / gross_absolute,
        "opposing_side_share_of_dominant_side": smaller / dominant if dominant else 0.0,
        "gross_absolute_to_absolute_net_multiple": gross_absolute / abs(net) if net else None,
    }


def quantile_metrics(values: np.ndarray) -> dict[str, float]:
    absolute = np.abs(np.asarray(values, dtype=float))
    quantiles = np.quantile(absolute, [0.25, 0.5, 0.75, 0.9, 0.95])
    return {
        "absolute_component_p25": float(quantiles[0]),
        "absolute_component_median": float(quantiles[1]),
        "absolute_component_p75": float(quantiles[2]),
        "absolute_component_p90": float(quantiles[3]),
        "absolute_component_p95": float(quantiles[4]),
        "absolute_component_maximum": float(absolute.max()),
        "absolute_component_mean": float(absolute.mean()),
    }


def concentration_metrics(frame: pd.DataFrame, label_column: str) -> dict[str, Any]:
    ranked = frame.assign(absolute=frame[VALUE].abs()).sort_values("absolute", ascending=False).reset_index(drop=True)
    total = float(ranked.absolute.sum())
    require(total > 0, "concentration denominator is zero")
    result: dict[str, Any] = {
        "top_1_share_of_gross_absolute": float(ranked.head(1).absolute.sum() / total),
        "top_3_share_of_gross_absolute": float(ranked.head(3).absolute.sum() / total),
        "top_5_share_of_gross_absolute": float(ranked.head(5).absolute.sum() / total),
        "top_10_share_of_gross_absolute": float(ranked.head(10).absolute.sum() / total),
        "top_5_by_absolute_component": [
            {label_column: str(row[label_column]), "component": float(row[VALUE]), "absolute_share": float(row.absolute / total)}
            for _, row in ranked.head(5).iterrows()
        ],
    }
    return result


def design_summary(frame: pd.DataFrame) -> dict[str, Any]:
    records = []
    for key, part in frame.groupby(KEYS, sort=True):
        metrics = signed_metrics(part[VALUE].to_numpy(float))
        records.append({**dict(zip(KEYS, key)), **metrics})
    design = pd.DataFrame(records)
    summary = {}
    for channel in CHANNELS:
        part = design.loc[design.channel.eq(channel)]
        cancellation = part.cancellation_fraction_of_gross_absolute.to_numpy(float)
        multiples = part.gross_absolute_to_absolute_net_multiple.dropna().to_numpy(float)
        summary[channel] = {
            "design_cells": int(len(part)),
            "positive_net_cells": int(part.net.gt(0).sum()),
            "negative_net_cells": int(part.net.lt(0).sum()),
            "cancellation_fraction_minimum": float(cancellation.min()),
            "cancellation_fraction_median": float(np.median(cancellation)),
            "cancellation_fraction_maximum": float(cancellation.max()),
            "gross_absolute_to_absolute_net_multiple_median": float(np.median(multiples)),
            "gross_absolute_to_absolute_net_multiple_maximum": float(multiples.max()),
        }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-receipt", type=Path, required=True)
    parser.add_argument("--country", type=Path, required=True)
    parser.add_argument("--region", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--memory-cap-bytes", type=int, default=536870912)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh heterogeneity audit output required")
    source = json.loads(args.source_receipt.read_text(encoding="utf-8"))
    require(source["schema"] == "peeps_monthly_scc_country_decomposition/v1", "source receipt schema differs")
    require(source["outputs"]["country"]["sha256"] == digest(args.country), "country table hash differs")
    require(source["outputs"]["region"]["sha256"] == digest(args.region), "region table hash differs")
    require(source["claim_gates"] == {
        "country_accounting": True,
        "country_causal_effect": False,
        "country_total_damage": False,
        "paired_replacement_scc": False,
    }, "source claim gates differ")

    country = pd.read_csv(args.country)
    region = pd.read_csv(args.region)
    require(len(country) == int(source["support"]["country_rows"]), "country row count differs")
    require(len(region) == int(source["support"]["region_rows"]), "region row count differs")
    require(country.iso3.nunique() == int(source["support"]["countries"]), "country support differs")
    require(region.fund_region.nunique() == int(source["support"]["fund_regions_including_unmapped"]), "region support differs")
    require(set(country.channel.unique()) == set(CHANNELS) == set(region.channel.unique()), "channel support differs")
    require(np.isfinite(country[VALUE]).all() and np.isfinite(region[VALUE]).all(), "component table is nonfinite")

    regrouped = country.groupby(["fund_region", *KEYS], as_index=False)[VALUE].sum().sort_values(["fund_region", *KEYS]).reset_index(drop=True)
    registered = region[["fund_region", *KEYS, VALUE]].sort_values(["fund_region", *KEYS]).reset_index(drop=True)
    require(regrouped[["fund_region", *KEYS]].equals(registered[["fund_region", *KEYS]]), "country/region keys differ")
    region_error = float(np.max(np.abs(regrouped[VALUE] - registered[VALUE])))
    require(region_error <= 1e-15, "country-to-region aggregation differs")

    minimum_pulse = float(country.pulse_size_gtc.min())
    central_filter = country.pulse_size_gtc.eq(minimum_pulse) & country.adaptation.eq("fixed") & country.discount_rate_label.eq("2.0%")
    central_country = country.loc[central_filter].copy()
    central_region = region.loc[region.pulse_size_gtc.eq(minimum_pulse) & region.adaptation.eq("fixed") & region.discount_rate_label.eq("2.0%")].copy()
    require(len(central_country) == country.iso3.nunique() * len(CHANNELS), "central country support differs")
    require(len(central_region) == region.fund_region.nunique() * len(CHANNELS), "central region support differs")

    central = {"country": {}, "region_including_unmapped": {}, "fund_region_excluding_unmapped": {}}
    for channel in CHANNELS:
        countries = central_country.loc[central_country.channel.eq(channel)].copy()
        regions = central_region.loc[central_region.channel.eq(channel)].copy()
        central["country"][channel] = {
            **signed_metrics(countries[VALUE].to_numpy(float)),
            "absolute_component_distribution": quantile_metrics(countries[VALUE].to_numpy(float)),
            "concentration": concentration_metrics(countries, "iso3"),
        }
        central["region_including_unmapped"][channel] = {
            **signed_metrics(regions[VALUE].to_numpy(float)),
            "absolute_component_distribution": quantile_metrics(regions[VALUE].to_numpy(float)),
            "concentration": concentration_metrics(regions, "fund_region"),
        }
        fund_regions = regions.loc[regions.fund_region.ne("UNMAPPED")].copy()
        central["fund_region_excluding_unmapped"][channel] = {
            **signed_metrics(fund_regions[VALUE].to_numpy(float)),
            "absolute_component_distribution": quantile_metrics(fund_regions[VALUE].to_numpy(float)),
            "concentration": concentration_metrics(fund_regions, "fund_region"),
        }

    joint_country = central_country.loc[central_country.channel.eq("joint_monthly_pattern")].copy()
    joint_region = central_region.loc[central_region.channel.eq("joint_monthly_pattern")].copy()
    net = float(joint_country[VALUE].sum())
    gross_country = float(joint_country[VALUE].abs().sum())
    gross_region = float(joint_region[VALUE].abs().sum())
    require(abs(net - float(joint_region[VALUE].sum())) <= 1e-15, "country and region nets differ")
    require(gross_country + 1e-18 >= gross_region + 1e-18 >= abs(net), "cancellation hierarchy differs")
    cancellation_decomposition = {
        "country_gross_absolute": gross_country,
        "region_gross_absolute_including_unmapped": gross_region,
        "absolute_global_net": abs(net),
        "within_region_country_netting_amount": gross_country - gross_region,
        "between_region_netting_amount": gross_region - abs(net),
        "total_netting_amount": gross_country - abs(net),
        "within_region_share_of_country_gross_absolute": (gross_country - gross_region) / gross_country,
        "between_region_share_of_country_gross_absolute": (gross_region - abs(net)) / gross_country,
        "total_cancellation_fraction_of_country_gross_absolute": (gross_country - abs(net)) / gross_country,
    }
    require(abs(
        cancellation_decomposition["within_region_share_of_country_gross_absolute"]
        + cancellation_decomposition["between_region_share_of_country_gross_absolute"]
        - cancellation_decomposition["total_cancellation_fraction_of_country_gross_absolute"]
    ) <= 1e-14, "cancellation decomposition does not close")

    country_scale = quantile_metrics(joint_country[VALUE].to_numpy(float))
    country_scale.update({
        "countries_with_absolute_component_above_absolute_global_net": int(joint_country[VALUE].abs().gt(abs(net)).sum()),
        "countries_below_1pct_of_country_gross_absolute": int(joint_country[VALUE].abs().lt(0.01 * gross_country).sum()),
        "countries_below_5pct_of_country_gross_absolute": int(joint_country[VALUE].abs().lt(0.05 * gross_country).sum()),
        "warning": "These are country accounting components, not local biophysical effect sizes.",
    })

    pivot = central_country.pivot(index="iso3", columns="channel", values=VALUE)
    quantity = pivot["quantity_reference"].to_numpy(float)
    timing = pivot["timing_increment"].to_numpy(float)
    joint = pivot["joint_monthly_pattern"].to_numpy(float)
    require(float(np.max(np.abs(quantity + timing - joint))) <= 1e-15, "central country channel identity differs")
    timing_interaction = {
        "timing_amplifies_quantity_sign_countries": int(np.sum(quantity * timing > 0)),
        "timing_offsets_quantity_sign_countries": int(np.sum(quantity * timing < 0)),
        "timing_or_quantity_exact_zero_countries": int(np.sum(quantity * timing == 0)),
        "timing_changes_quantity_to_joint_sign_countries": int(np.sum(np.sign(quantity) != np.sign(joint))),
        "gross_absolute_timing_share_of_gross_absolute_joint": float(np.abs(timing).sum() / np.abs(joint).sum()),
        "countries_where_absolute_timing_exceeds_absolute_quantity": int(np.sum(np.abs(timing) > np.abs(quantity))),
        "countries_where_absolute_timing_exceeds_absolute_joint": int(np.sum(np.abs(timing) > np.abs(joint))),
    }

    internal_regions = []
    for fund_region, part in joint_country.groupby("fund_region", sort=True):
        metrics = signed_metrics(part[VALUE].to_numpy(float))
        internal_regions.append({"fund_region": fund_region, "countries": int(len(part)), **metrics})
    internal_regions.sort(key=lambda item: item["gross_absolute"], reverse=True)

    result = {
        "schema": "peeps_monthly_scc_heterogeneity_audit/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_accounting_cancellation_audit_not_local_effects_or_final_scc",
        "definition": "country and FUND-region sign, scale, concentration, and cancellation audit of the validated PEEPS monthly precipitation SCC diagnostic",
        "central_design": {
            "pulse_size_gtc": minimum_pulse,
            "adaptation": "fixed",
            "discount_rate_label": "2.0%",
            **central,
            "joint_cancellation_decomposition": cancellation_decomposition,
            "joint_country_accounting_scale": country_scale,
            "timing_quantity_interaction": timing_interaction,
            "within_region_country_components": internal_regions,
        },
        "all_registered_design_cells": {
            "country": design_summary(country),
            "region_including_unmapped": design_summary(region),
        },
        "validation": {
            "country_to_region_maximum_absolute_error": region_error,
            "central_country_channel_identity_maximum_absolute_error": float(np.max(np.abs(quantity + timing - joint))),
            "cancellation_decomposition_closes": True,
        },
        "sources": {
            "source_receipt": {"path": str(args.source_receipt), "sha256": digest(args.source_receipt)},
            "country": {"path": str(args.country), "sha256": digest(args.country)},
            "region": {"path": str(args.region), "sha256": digest(args.region)},
        },
        "claim_gates": {
            "accounting_decomposition": True,
            "local_biophysical_effect": False,
            "country_causal_effect": False,
            "country_total_damage": False,
            "representative_global_precipitation_scc": False,
            "paired_give_agriculture_replacement": False,
        },
        "limitations": [
            "One ESM/scenario, maize only, and monthly mean precipitation.",
            "Country and FUND-region values are accounting contributions under separate national maize markets, not local causal or biophysical effects.",
            "Aggregation can cancel signed components within FUND regions and again across regions; neither level identifies household welfare incidence.",
            "Antigua and Barbuda remains UNMAPPED because the archived crosswalk has no assignment.",
            "Daily drought, extremes, other crops, trade, storage, and adaptation costs are omitted.",
            "Standard deterministic GIVE discount factors retain Moore agriculture; this is not a paired agriculture replacement or final SCC.",
        ],
        "resources": {
            "peak_rss_bytes": peak_rss_bytes(),
            "memory_cap_bytes": int(args.memory_cap_bytes),
            "memory_gate_passed": True,
        },
        "implementation": {
            "path": str(Path(__file__).resolve()),
            "sha256": digest(Path(__file__).resolve()),
        },
    }
    require(result["resources"]["peak_rss_bytes"] < int(args.memory_cap_bytes), "heterogeneity audit memory cap exceeded")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "central_joint_country": central["country"]["joint_monthly_pattern"],
        "cancellation_decomposition": cancellation_decomposition,
        "country_scale": country_scale,
        "timing_interaction": timing_interaction,
        "resources": result["resources"],
    }, indent=2))


if __name__ == "__main__":
    main()

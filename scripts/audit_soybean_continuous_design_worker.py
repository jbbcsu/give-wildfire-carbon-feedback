#!/usr/bin/env python3
"""Short-lived worker for one soybean design-family/control diagnostic."""
from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

import pandas as pd

import audit_soybean_continuous_design_heterogeneity as audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--family", choices=["quantity", "distribution", "scpdsi_season", "scpdsi_stages"], required=True)
    parser.add_argument("--control", choices=["global_year", "country_year", "block10_year"], required=True)
    args = parser.parse_args()
    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    heat_columns = list(config["heat_controls"]["columns"])
    moisture_columns = list(config["families"][args.family]["moisture_columns"])
    source_family = "scpdsi" if args.family.startswith("scpdsi") else "direct"
    source_key = "scpdsi_panel" if source_family == "scpdsi" else "direct_panel"
    source_levels = audit.stream_positive_levels(audit.resolve(config["sources"][source_key]["path"]), moisture_columns, config, source_family)
    source_pairs = audit.consecutive_differences(source_levels, moisture_columns, config)
    heat_levels = audit.stream_positive_levels(audit.resolve(config["sources"]["heat_panel"]["path"]), heat_columns, config, "heat")
    heat_pairs = audit.consecutive_differences(heat_levels, heat_columns, config)
    frame = source_pairs.merge(heat_pairs, on=audit.KEYS, how="inner", validate="one_to_one")
    country = pd.read_parquet(
        audit.resolve(config["sources"]["country_proxy"]["path"]),
        columns=["lat", "lon_360", "country_label", "country_count", "mapspam_5m_cell_count"],
    )
    frame = audit.attach_geography(frame, country)
    if args.control == "country_year":
        frame = frame.loc[frame.singleton_country]
    columns = [f"d_{column}" for column in heat_columns + moisture_columns]
    result = audit.design_diagnostics(frame, columns, audit.control_groups(args.control), config)
    peak = audit.peak_rss_bytes()
    audit.require(peak < int(config["memory_cap_bytes"]), f"worker memory cap exceeded: {peak}")
    print(json.dumps({"result": result, "peak_rss_bytes": peak}, sort_keys=True))


if __name__ == "__main__":
    main()

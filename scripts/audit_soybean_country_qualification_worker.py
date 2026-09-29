#!/usr/bin/env python3
"""Short-lived worker for soybean country-support qualification."""
from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

import audit_soybean_continuous_design_heterogeneity as audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = tomllib.loads(args.config.read_text(encoding="utf-8"))
    heat_columns = list(config["heat_controls"]["columns"])
    moisture_columns = list(config["families"]["quantity"]["moisture_columns"])
    direct_levels = audit.stream_positive_levels(audit.resolve(config["sources"]["direct_panel"]["path"]), moisture_columns, config, "direct")
    direct_pairs = audit.consecutive_differences(direct_levels, moisture_columns, config)
    heat_levels = audit.stream_positive_levels(audit.resolve(config["sources"]["heat_panel"]["path"]), heat_columns, config, "heat")
    heat_pairs = audit.consecutive_differences(heat_levels, heat_columns, config)
    frame = direct_pairs.merge(heat_pairs, on=audit.KEYS, how="inner", validate="one_to_one")
    country = pd.read_parquet(
        audit.resolve(config["sources"]["country_proxy"]["path"]),
        columns=["lat", "lon_360", "country_label", "country_count", "mapspam_5m_cell_count"],
    )
    frame = audit.attach_geography(frame, country)
    moisture = "d_log1p_precip_mm"
    frame = frame.loc[np.isfinite(frame[moisture])]
    quantiles = np.quantile(frame[moisture].to_numpy(dtype=float), [0.01, 0.05, 0.5, 0.95, 0.99])
    low, high = float(quantiles[1]), float(quantiles[3])
    singleton = frame.loc[frame.singleton_country]
    country_variation = audit.geography_variation(singleton, "country_label", moisture, low, high)
    block_variation = audit.geography_variation(frame, "block10", moisture, low, high)
    columns = [f"d_{column}" for column in heat_columns + moisture_columns]
    details, gate = audit.qualify_countries(frame, columns, low, high, config)
    peak = audit.peak_rss_bytes()
    audit.require(peak < int(config["memory_cap_bytes"]), f"country worker memory cap exceeded: {peak}")
    print(json.dumps({
        "global_low": low, "global_high": high,
        "global_variation": audit.variation_record(frame[moisture].to_numpy(dtype=float), low, high),
        "country_variation": country_variation, "block_variation": block_variation,
        "country_details": details, "country_gate": gate, "peak_rss_bytes": peak,
    }, sort_keys=True))


if __name__ == "__main__":
    main()

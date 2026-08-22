#!/usr/bin/env python3
"""Join a chosen historical scPDSI benchmark to a crop-year panel safely."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from build_crop_stage_scpdsi_features import KEYS
from validate_stage_scpdsi_partition import validate_frame


METRICS = ["scpdsi_mean", "scpdsi_min", "scpdsi_days_at_or_below_threshold"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", required=True)
    parser.add_argument("--stage-scpdsi", required=True)
    parser.add_argument("--threshold", type=float, required=True)
    parser.add_argument("--expected-stages", type=int, default=3)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    panel = pd.read_parquet(args.panel)
    drought = pd.read_parquet(args.stage_scpdsi)
    validate_frame(drought, args.threshold, args.expected_stages)
    if panel.duplicated(KEYS).any():
        raise ValueError("Panel has duplicate crop-year/grid keys")
    if drought.empty:
        raise ValueError("Stage scPDSI input is empty")
    if not np.isfinite(drought[METRICS].to_numpy(dtype=float)).all():
        raise ValueError("Stage scPDSI metrics contain nonfinite values")
    wide = drought.pivot(index=KEYS, columns="stage_id", values=METRICS)
    wide.columns = [f"stage{stage_id}_{name}" for name, stage_id in wide.columns]
    wide = wide.reset_index()
    added = (set(wide.columns) - set(KEYS)) | {
        "scpdsi_threshold", "drought_index_name", "drought_source_role",
    }
    if overlap := added & set(panel.columns):
        raise ValueError(f"Panel already contains stage scPDSI output columns {sorted(overlap)}")
    joined = panel.merge(wide, on=KEYS, how="left", validate="one_to_one", indicator=True)
    if not joined._merge.eq("both").all() or len(joined) != len(panel):
        raise ValueError("Stage scPDSI join does not cover every panel row exactly once")
    joined = joined.drop(columns="_merge")
    joined["scpdsi_threshold"] = args.threshold
    joined["drought_index_name"] = "CRU_TS_scpdsi"
    joined["drought_source_role"] = "historical_benchmark_not_future_scc_input"
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    joined.to_parquet(output, index=False)
    print(f"wrote {len(joined)} rows with historical scPDSI benchmark features")


if __name__ == "__main__":
    main()

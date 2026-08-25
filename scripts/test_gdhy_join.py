#!/usr/bin/env python3
"""Run the real pilot feature-to-GDHY coordinate join and verify its invariants."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd


project = Path(__file__).resolve().parents[1]
features = project / "data/interim/pilot_maize_noirr_lat100_102_1982_1989.parquet"
if not features.exists():
    raise SystemExit("Build the pilot feature partition before this integration check.")
out = project / "data/interim/pilot_maize_noirr_with_gdhy.parquet"
subprocess.run([
    sys.executable, str(project / "scripts/join_gdhy_yields.py"),
    "--features", str(features), "--gdhy-root", str(project / "data/raw/gdhy_v1.2_v1.3"),
    "--out", str(out),
], check=True)
panel = pd.read_parquet(out)
assert not panel.duplicated(["harvest_year", "lat", "lon_360", "crop", "irrigation"]).any()
assert panel.yield_observed.any()
assert (panel.loc[panel.yield_observed, "yield_t_ha"] > 0).all()
assert panel.yield_nonpositive.dtype == bool
assert panel.loc[panel.yield_nonpositive, "yield_t_ha"].isna().all()
assert panel.loc[panel.yield_nonpositive, "gdhy_yield_raw_t_ha"].eq(0).all()
print(f"GDHY pilot join passed; coverage={panel.yield_observed.mean():.3f}")

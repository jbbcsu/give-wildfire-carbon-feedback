#!/usr/bin/env python3
"""Synthetic support and boundary test for the agricultural exposure adapter."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SCRIPT = HERE / "adapt_usdm_agricultural_exposures.py"
CONFIG = ROOT / "config/usdm_kuwayama_agricultural_area_cultivated_v1.toml"


def main() -> None:
    rows = []
    for mask in ("cultivated_agriculture", "broad_agriculture"):
        for geoid in ("01001", "01003"):
            for year in range(2001, 2014):
                days = 366 if pd.Timestamp(year, 1, 1).is_leap_year else 365
                rows.append({
                    "county_geoid": geoid,
                    "mask_id": mask,
                    "harvest_year": year,
                    "represented_days": days,
                    "total_equivalent_weeks": days / 7,
                    "analysis_role": "historical_agricultural_area_validation_only",
                    "scc_authorized": False,
                    "weeks_none": days / 7 - 15,
                    **{f"weeks_d{level}": 3.0 for level in range(5)},
                })
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / "source.parquet"
        output = root / "output.parquet"
        audit = root / "audit.json"
        pd.DataFrame(rows).to_parquet(source, index=False)
        subprocess.run([
            sys.executable, str(SCRIPT), "--config", str(CONFIG), "--exposure", str(source),
            "--out", str(output), "--audit-out", str(audit),
        ], check=True)
        result = pd.read_parquet(output)
        assert len(result) == 52
        assert set(result.outcome_crop) == {"corn_grain", "soybeans"}
        assert set(result.source_area_basis) == {
            "cdl_2008_cultivated_agriculture_3960m_approximation"
        }
        assert not result.scc_authorized.any()
        assert not result.duplicated(["county_geoid", "outcome_crop", "harvest_year"]).any()
    print("agricultural exposure adapter test passed")


if __name__ == "__main__":
    main()

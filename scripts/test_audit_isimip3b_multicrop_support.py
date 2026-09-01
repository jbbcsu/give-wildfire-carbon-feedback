#!/usr/bin/env python3
"""Synthetic failure-mode tests for the bounded multi-crop support audit."""
from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import pandas as pd

from audit_isimip3b_multicrop_support import audit


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def season(irrigation: str, offset: float = 0.0) -> pd.DataFrame:
    return pd.DataFrame({
        "harvest_year": [2042, 2042], "lat": [1.0, 1.0], "lon_360": [2.0, 3.0],
        "crop": ["soy", "soy"], "irrigation": [irrigation, irrigation],
        "season_days": [10, 10], "tmean_c": [20.0 + offset, 21.0 + offset],
        "precip_mm": [30.0 + offset, 60.0 + offset], "wet_days_n": [3, 6],
        "cdd_max_days": [4, 2], "rx1day_mm": [10.0, 20.0], "rx5day_mm": [20.0, 40.0],
    })


def stages(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in frame.to_dict("records"):
        for stage, share, days in ((1, 0.2, 3), (2, 0.3, 4), (3, 0.5, 3)):
            rows.append({
                **{key: row[key] for key in ["harvest_year", "lat", "lon_360", "crop", "irrigation"]},
                "stage_id": stage, "stage_days": days, "precip_mm": row["precip_mm"] * share,
                "wet_days_n": ([1, 1, 1] if row["wet_days_n"] == 3 else [1, 2, 3])[stage - 1],
                "cdd_max_days": min(row["cdd_max_days"], days),
                "rx1day_mm": row["rx1day_mm"] if stage == 3 else row["rx1day_mm"] * share,
                "rx5day_mm": row["precip_mm"] * share,
            })
    return pd.DataFrame(rows)


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    (root / "config").mkdir()
    (root / "inputs").mkdir()
    source_paths = []
    for scenario in ("ssp126", "ssp585"):
        path = root / "inputs" / f"{scenario}.toml"
        path.write_text("version = 1\n")
        source_paths.append(path)
    cell_lines = []
    for cell_id, irrigation in (("soy_noirr", "noirr"), ("soy_firr", "firr")):
        calendar = root / "inputs" / f"{cell_id}.nc"
        calendar.write_bytes(cell_id.encode())
        paths = {}
        for scenario, label, offset in (("ssp126", "reference", 0.0), ("ssp585", "candidate", 1.0)):
            base = season(irrigation, offset)
            for kind, frame in (("season", base), ("stages", stages(base))):
                path = root / "inputs" / f"{cell_id}_{scenario}_{kind}.parquet"
                frame.to_parquet(path, index=False)
                paths[f"{label}_{kind}"] = path.relative_to(root)
        cell_lines.append(f'''\n[[cells]]
id = "{cell_id}"
crop = "soy"
irrigation = "{irrigation}"
calendar = "{calendar.relative_to(root)}"
calendar_sha256 = "{digest(calendar)}"
reference_season = "{paths['reference_season']}"
reference_stages = "{paths['reference_stages']}"
candidate_season = "{paths['candidate_season']}"
candidate_stages = "{paths['candidate_stages']}"
''')
    config = root / "config" / "test.toml"
    config.write_text(f'''schema_version = 1
role = "test"
esm = "test-esm"
member = "r1"
reference_scenario = "ssp126"
candidate_scenario = "ssp585"
year_start = 2042
year_end = 2042
expected_season_rows_per_cell = 2
expected_stage_rows_per_cell = 6
expected_stages = 3
required_cells = ["soy_noirr", "soy_firr"]

[[source_provenance]]
scenario = "ssp126"
path = "{source_paths[0].relative_to(root)}"
sha256 = "{digest(source_paths[0])}"

[[source_provenance]]
scenario = "ssp585"
path = "{source_paths[1].relative_to(root)}"
sha256 = "{digest(source_paths[1])}"
{''.join(cell_lines)}''')
    result = audit(config, root)
    assert result["result"] == "passed"
    assert len(result["cells"]) == 2
    assert result["gates"]["bounded_multicrop_feature_support"] is True
    assert result["gates"]["damage_or_scc_input"] is False

    original = source_paths[0].read_text()
    source_paths[0].write_text(original + "changed = true\n")
    try:
        audit(config, root)
    except ValueError as error:
        assert "hash mismatch" in str(error), error
    else:
        raise AssertionError("changed source provenance should fail closed")

print("bounded multi-crop support audit synthetic tests passed")

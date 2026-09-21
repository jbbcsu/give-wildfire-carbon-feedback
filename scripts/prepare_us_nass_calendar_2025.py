#!/usr/bin/env python3
"""Extend the pinned NASS usual-date crop calendar, requiring old overlap parity."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data/raw/us_county/crop_calendar/fcdate10.pdf"
OLD = ROOT / "data/interim/us_county/nass_usual_date_calendars_1981_2022.csv"
BUILDER = ROOT / "us_county_validation/scripts/build_nass_usual_date_calendars.py"
PROTOCOL = ROOT / "US_COUNTY_AVERAGE_CROP_YEAR_FEATURE_PROTOCOL_20260916.md"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "data/interim"):
        raise ValueError("fresh ignored calendar extension output directory required")
    out.mkdir(parents=True)
    calendar_path = out / "nass_usual_date_calendars_1981_2025.csv"
    definitions_path = out / "source_definitions.csv"
    audit_path = out / "source_audit.json"
    subprocess.run([sys.executable, "-B", str(BUILDER), "--pdf", str(PDF),
                    "--year-min", "1981", "--year-max", "2025",
                    "--definitions-out", str(definitions_path),
                    "--calendar-out", str(calendar_path),
                    "--audit-out", str(audit_path)], check=True)
    old = pd.read_csv(OLD).sort_values(
        ["state", "calendar_crop", "harvest_year", "calendar_role"]).reset_index(drop=True)
    new = pd.read_csv(calendar_path)
    overlap = new.loc[new.harvest_year.le(2022)].sort_values(
        ["state", "calendar_crop", "harvest_year", "calendar_role"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(old, overlap, check_dtype=False, check_exact=True)
    audit = json.loads(audit_path.read_text())
    if audit["harvest_year_min"] != 1981 or audit["harvest_year_max"] != 2025:
        raise ValueError("NASS calendar extension audit year range differs")
    result = {"status": "nass_calendar_1981_2025_overlap_validated",
              "source_pdf_sha256": sha(PDF), "prior_calendar_sha256": sha(OLD),
              "source_builder_sha256": sha(BUILDER), "protocol_sha256": sha(PROTOCOL),
              "calendar_sha256": sha(calendar_path),
              "source_definitions_sha256": sha(definitions_path),
              "source_audit_sha256": sha(audit_path),
              "prior_rows_reproduced": len(old), "calendar_rows": len(new),
              "new_rows_2023_2025": int(new.harvest_year.ge(2023).sum()),
              "yield_outcomes_read": False, "response_or_scc_estimated": False,
              "code_sha256": sha(Path(__file__))}
    (out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"],
                      "prior_rows_reproduced": len(old),
                      "new_rows_2023_2025": result["new_rows_2023_2025"]}))


if __name__ == "__main__":
    main()

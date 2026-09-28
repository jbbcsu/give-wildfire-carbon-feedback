#!/usr/bin/env python3
"""Validate fixed sorghum/cotton calendars and exact paired-outcome coverage."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--definitions", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--validation-out", type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text())
    definitions = pd.read_csv(args.definitions)
    calendar = pd.read_csv(args.calendar)
    panel = pd.read_parquet(args.panel)
    require(digest(ROOT / receipt["implementation"]["path"]) == receipt["implementation"]["sha256"], "builder hash differs")
    require(digest(args.definitions) == receipt["definitions"]["sha256"], "definition hash differs")
    require(digest(args.calendar) == receipt["calendar"]["sha256"], "calendar hash differs")
    require(definitions.groupby("calendar_crop").size().to_dict() == {"cotton_upland": 17, "sorghum_grain": 14}, "source row counts differ")
    require(not calendar.duplicated(["calendar_crop", "state", "harvest_year", "calendar_role"]).any(), "duplicate key")
    require(set(calendar.calendar_role) == {"fixed_primary", "fixed_broad_window_sensitivity"}, "role set differs")
    starts, ends = pd.to_datetime(calendar.season_start), pd.to_datetime(calendar.season_end)
    require((starts <= ends).all() and ends.dt.year.sub(calendar.harvest_year).isin([0, 1]).all(), "calendar chronology differs")
    require((ends.sub(starts).dt.days.add(1).between(30, 500)).all(), "calendar duration differs")
    require(calendar.feature_construction_eligible.eq(True).all(), "feature gate closed")
    require(calendar.response_estimation_authorized.eq(False).all() and calendar.scc_authorized.eq(False).all(), "downstream gate opened")
    for (_, _, role), group in calendar.groupby(["calendar_crop", "state", "calendar_role"]):
        require(group.season_start.str[5:].nunique() == 1 and group.season_end.str[5:].nunique() == 1, "fixed month/day changed")
    anchors = calendar.set_index(["calendar_crop", "state", "harvest_year", "calendar_role"])
    expected = {
        ("cotton_upland", "AR", 1981, "fixed_primary"): ("1981-05-11", "1981-10-18"),
        ("cotton_upland", "TX", 1981, "fixed_broad_window_sensitivity"): ("1981-03-22", "1982-01-11"),
        ("sorghum_grain", "KS", 1981, "fixed_primary"): ("1981-06-02", "1981-10-18"),
    }
    for key, dates in expected.items():
        row = anchors.loc[key]
        require((row.season_start, row.season_end) == dates, f"anchor differs: {key}")
    support = panel[["crop", "state_alpha", "harvest_year", "county_geoid"]].drop_duplicates()
    joined = support.merge(calendar, left_on=["crop", "state_alpha", "harvest_year"], right_on=["calendar_crop", "state", "harvest_year"], how="left")
    coverage = joined.groupby(["crop", "state_alpha", "harvest_year", "county_geoid"]).calendar_role.nunique()
    require(len(coverage) == len(support) and coverage.eq(2).all(), "outcome/calendar coverage differs")
    result = {
        "status": "validated_calendar_and_exact_outcome_support",
        "definition_rows": len(definitions), "calendar_rows": len(calendar),
        "paired_outcome_keys": len(support), "paired_outcome_keys_with_both_roles": int(coverage.eq(2).sum()),
        "source_anchors_checked": len(expected), "same_calendar_for_both_practices": True,
        "validator_sha256": digest(Path(__file__)),
        "weather_joined": False, "response_estimation_authorized": False, "scc_authorized": False,
    }
    args.validation_out.parent.mkdir(parents=True, exist_ok=True)
    args.validation_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

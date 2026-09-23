#!/usr/bin/env python3
"""Unit tests for continental county support selection used by the merge."""
from __future__ import annotations

import csv
import tempfile
from pathlib import Path

from merge_usdm_national_990m_state_partitions import expected_states_and_counties


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "inventory.csv"
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=["county_geoid", "classifier_eligible"])
            writer.writeheader()
            writer.writerows([
                {"county_geoid": "01001", "classifier_eligible": "true"},
                {"county_geoid": "02013", "classifier_eligible": "true"},
                {"county_geoid": "04001", "classifier_eligible": "false"},
                {"county_geoid": "06001", "classifier_eligible": "1"},
            ])
        states, counties = expected_states_and_counties(path)
        assert states == ["01", "06"]
        assert counties == {"01001", "06001"}
    print("national 990 m partition merge helper tests passed")


if __name__ == "__main__":
    main()

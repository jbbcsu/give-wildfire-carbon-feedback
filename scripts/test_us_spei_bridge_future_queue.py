#!/usr/bin/env python3
"""Focused integrity tests for the deterministic future bridge queue."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    path = ROOT / "data/provenance/us_spei_bridge_future_11_cell_queue_20261013.json"
    queue = json.loads(path.read_text())
    assert queue["schema"] == "us_spei_bridge_future_11_cell_queue_v1"
    assert queue["status"] == "ready_for_sequential_execution"
    assert queue["case_count"] == len(queue["cases"]) == 15
    assert queue["extrema_object_count"] == 30
    assert queue["historical_fit"]["cells"] == 11 and queue["historical_fit"]["fits"] == 396
    assert not any(queue["gates"].values())
    assert [item["case_number"] for item in queue["cases"]] == list(range(1, 16))
    assert len({(item["esm"], item["scenario"]) for item in queue["cases"]}) == 15
    assert all({item["variable"] for item in case["extrema"]} == {"tasmin", "tasmax"}
               for case in queue["cases"])
    assert len({item["sha512"] for case in queue["cases"] for item in case["extrema"]}) == 30
    assert all(item["file_url"].startswith("https://files.isimip.org/")
               for case in queue["cases"] for item in case["extrema"])
    assert queue["execution_rules"] == {
        "evict_only_after_independent_validation": True, "maximum_resident_extrema_pairs": 1,
        "memory_limit_mib_per_job": 512, "minimum_free_disk_gib": 130,
        "retain_precipitation_and_mean_temperature": True, "stop_on_first_failure": True,
    }
    print("PASS: 12 future 11-cell SPEI queue checks")


if __name__ == "__main__":
    main()

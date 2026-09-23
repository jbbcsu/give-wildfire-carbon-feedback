#!/usr/bin/env python3
"""Unit tests for deterministic whole-county grid chunk assignment."""
from __future__ import annotations

from collections import Counter

from split_cdl_agricultural_grid_by_county import assign_chunks


def main() -> None:
    counts = Counter({"01001": 4, "01003": 6, "01005": 2, "01007": 8})
    assert assign_chunks(counts, 10) == [["01001", "01003"], ["01005", "01007"]]
    assert assign_chunks(counts, 20) == [["01001", "01003", "01005", "01007"]]
    try:
        assign_chunks(counts, 7)
    except ValueError as error:
        assert "01007" in str(error)
    else:
        raise AssertionError("oversized county was accepted")
    print("whole-county agricultural-grid chunk tests passed")


if __name__ == "__main__":
    main()

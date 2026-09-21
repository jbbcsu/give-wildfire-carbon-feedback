#!/usr/bin/env python3
"""Synthetic checks for the NASS state direct-practice count audit."""
from audit_nass_state_direct_practice_support import CROPS, PRACTICES, YEARS, parameters, summarize


def fixture(count: int = 10) -> list[dict]:
    return [{"crop": crop, "practice": practice, "year": year, "count": count}
            for crop in CROPS for practice in PRACTICES for year in YEARS]


def main() -> None:
    query = parameters("corn", "NON-IRRIGATED", 2025)
    assert query["agg_level_desc"] == "STATE"
    assert query["commodity_desc"] == "CORN"
    assert query["util_practice_desc"] == "GRAIN"
    assert "key" not in query
    result = summarize(fixture())
    assert result["query_count"] == 56
    assert all(row["state_panel_feasible"] for row in result["series"])
    rows = fixture()
    for row in rows:
        if row["crop"] == "soybean" and row["practice"] == "NON-IRRIGATED" and row["year"] == 2025:
            row["count"] = 7
    result = summarize(rows)
    target = [row for row in result["series"] if row["crop"] == "soybean" and row["practice"] == "NON-IRRIGATED"][0]
    assert target["state_panel_feasible"] is False
    try:
        summarize(fixture()[:-1])
    except ValueError:
        pass
    else:
        raise AssertionError("incomplete count matrix was accepted")
    print("NASS state direct-practice support synthetic checks passed")


if __name__ == "__main__":
    main()

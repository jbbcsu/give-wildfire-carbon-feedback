#!/usr/bin/env python3
"""Synthetic checks for the Census direct-practice outcome count audit."""
from audit_nass_census_direct_practice_outcome_support import (
    CROPS, PRACTICES, STATISTICS, YEARS, parameters, summarize,
)


def fixture(count: int = 100) -> list[dict]:
    return [{"crop": crop, "practice": practice, "year": year,
             "statistic": statistic, "count": count}
            for crop in CROPS for practice in PRACTICES for year in YEARS for statistic in STATISTICS]


def main() -> None:
    query = parameters("soybean", "NON-IRRIGATED", 2022, "production")
    assert query["source_desc"] == "CENSUS"
    assert query["agg_level_desc"] == "COUNTY"
    assert query["statisticcat_desc"] == "PRODUCTION"
    assert query["unit_desc"] == "BU"
    assert "key" not in query
    result = summarize(fixture())
    assert result["query_count"] == 24 and result["feasible_cells"] == 12
    rows = fixture()
    for row in rows:
        if row["crop"] == "corn" and row["practice"] == "IRRIGATED" and row["year"] == 2017 and row["statistic"] == "area":
            row["count"] = 99
    result = summarize(rows)
    assert result["feasible_cells"] == 11
    assert [row for row in result["cells"] if row["crop"] == "corn" and row["practice"] == "IRRIGATED" and row["year"] == 2017][0]["count_feasible"] is False
    try:
        summarize(fixture()[:-1])
    except ValueError:
        pass
    else:
        raise AssertionError("incomplete Census count matrix was accepted")
    print("NASS Census direct-practice outcome support synthetic checks passed")


if __name__ == "__main__":
    main()

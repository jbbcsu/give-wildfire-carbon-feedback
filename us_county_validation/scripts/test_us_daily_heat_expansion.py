#!/usr/bin/env python3
"""Synthetic invariants for the daily-heat expansion checkpoint."""
import pandas as pd

from build_us_daily_heat_expansion import county_batches, metric_names, validate_heat_partition


def fixture():
    row = {
        "county_geoid": "01001", "outcome_crop": "corn_grain", "harvest_year": 2000,
        "coefficients_emitted": False, "row_predictions_emitted": False,
        "causal_response_authorized": False, "scc_authorized": False,
    }
    for threshold in (29, 30):
        for prefix, value in (("stage1", 1.0), ("stage2", 2.0), ("stage3", 3.0), ("season", 6.0)):
            for original, column in metric_names(threshold, prefix).items():
                row[column] = value if original != "spatial_aggregation_gap_c_days" else 0.25
    return pd.DataFrame([row])


def rejected(frame, message):
    expected = frame[["county_geoid", "outcome_crop", "harvest_year"]]
    try:
        validate_heat_partition(frame, expected, [29.0, 30.0])
    except (ValueError, AssertionError):
        return
    raise AssertionError(message)


def main():
    assert county_batches(["01003", "01001", "01005"], 2) == [["01001", "01003"], ["01005"]]
    try:
        county_batches(["01001", "01001"], 2)
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate county support accepted")
    frame = fixture()
    validate_heat_partition(frame, frame[["county_geoid", "outcome_crop", "harvest_year"]], [29.0, 30.0])
    bad = frame.copy()
    bad.loc[0, "season_tmax_exceedance_29c_c_days"] = 7
    rejected(bad, "stage/season mismatch accepted")
    bad = frame.copy()
    bad.loc[0, "season_county_mean_first_tmax_exceedance_29c_c_days"] = 7
    rejected(bad, "convexity violation accepted")
    bad = frame.copy()
    bad.loc[0, "scc_authorized"] = True
    rejected(bad, "open SCC gate accepted")
    print("daily-heat expansion schema, additivity, convexity and gate tests passed")


if __name__ == "__main__":
    main()

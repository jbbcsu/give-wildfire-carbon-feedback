"""Synthetic endpoint tests; fixtures are not empirical results."""
import pandas as pd
from evaluate_moisture_tmax_sensitivity import add_tmax


def main():
    common = pd.DataFrame([dict(county_geoid='00001', outcome_crop='corn_grain',
        irrigation_practice='non_irrigated', harvest_year=2001,
        difference_previous_harvest_year=2000)])
    rows = []
    for year, value in [(2001, 3.), (2000, 2.)]:
        row = common.iloc[0].to_dict()
        row['harvest_year'] = year
        row.update({f'stage{i}_tmax_mean_c':value for i in [1,2,3]})
        rows.append(row)
    levels = pd.DataFrame(rows)
    actual, names = add_tmax(common, levels)
    assert len(names) == 6
    assert actual.d_stage1_tmax_mean_c.iloc[0] == 1
    assert actual.d_stage1_tmax_mean_c_squared.iloc[0] == 5
    for invalid in [levels.iloc[:1], pd.concat([levels, levels.iloc[:1]])]:
        try:
            add_tmax(common, invalid)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid endpoint support accepted')
    print('endpoint alignment, difference-of-squares, missing and duplicate checks passed')


if __name__ == '__main__':
    main()

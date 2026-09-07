"""Synthetic fixtures for heat transformations, not observed weather."""
import numpy as np
from build_daily_heat_pilot import heat_metrics


def main():
    result=heat_metrics(np.array([[28.,32.],[29.,29.]]),[.5,.5],29)
    assert result['cell_first_tmax_exceedance_c_days']==1.5
    assert result['county_mean_first_exceedance_c_days']==1
    assert result['cell_first_above_threshold_days']==.5
    for weights in [[.2,.2],[-1.,2.]]:
        try:
            heat_metrics(np.array([[28.,32.]]),weights,29)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid weights accepted')
    print('daily threshold, strict exceedance, aggregation order and weight tests passed')


if __name__=='__main__':
    main()

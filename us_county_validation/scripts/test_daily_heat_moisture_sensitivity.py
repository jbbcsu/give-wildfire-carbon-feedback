#!/usr/bin/env python3
import numpy as np
import pandas as pd
from evaluate_daily_heat_moisture_sensitivity import add_heat

def main():
    common=pd.DataFrame({'county_geoid':['01001'],'outcome_crop':['corn_grain'],'harvest_year':[2001],
                         'irrigation_practice':['irrigated'],'difference_previous_harvest_year':[2000]})
    rows=[]
    for year,value in [(2000,1.),(2001,3.)]:
        row={'county_geoid':'01001','outcome_crop':'corn_grain','harvest_year':year}
        for stage in (1,2,3):
            row[f'stage{stage}_tmax_exceedance_29c_c_days']=value+stage
            row[f'stage{stage}_tmax_days_gt_29c']=value+2*stage
        rows.append(row)
    result,names=add_heat(common,pd.DataFrame(rows),29)
    assert len(names)==6 and np.allclose(result[['d_'+name for name in names]],2)
    print('daily-heat endpoint and six-control difference test passed')

if __name__=='__main__': main()

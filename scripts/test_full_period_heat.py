"""Synthetic full-period source sequence and exact paired contrast tests."""
import copy
import unittest
import numpy as np
import pandas as pd
from heat_cutout_dates import date_contract
from extend_heat_cutout_two_crops import validate_sequence
from compare_paired_heat_climate import compare
from allocate_irrigation_heat_basis import heat_basis_feature_names


class FullPeriod(unittest.TestCase):
    def setUp(self):
        self.contracts=[dict(dataset_id='SYNTHETIC',dataset_version='v1',resource_doi='SYNTHETIC',specifiers={},
            expected_start_year=a,expected_end_year=a+9,expected_gregorian_daily_count=date_contract(a,a+9)[2],
            file_name=f'synthetic_{a}_{a+9}.nc') for a in (2031,2041,2051)]
        self.grids=[dict(lat=np.array([39.75,39.25]),lon=np.array([.25,.75]),
            first_time=np.datetime64(f'{a}-01-01'),last_time=np.datetime64(f'{a+9}-12-31')) for a in (2031,2041,2051)]
    def test_valid_sequence(self):
        validate_sequence(self.contracts,self.grids,2032,2059)
        validate_sequence(self.contracts[1:2],self.grids[1:2],2042,2049)
    def test_reject_lineage_grid_gap_overlap(self):
        for mode in ('gap','duplicate','reorder','version','grid','timestamp'):
            cs=copy.deepcopy(self.contracts);gs=copy.deepcopy(self.grids)
            if mode=='gap':cs.pop(1);gs.pop(1)
            if mode=='duplicate':cs[1]=cs[0]
            if mode=='reorder':cs.reverse();gs.reverse()
            if mode=='version':cs[1]['dataset_version']='other'
            if mode=='grid':gs[1]['lon']+=.01
            if mode=='timestamp':gs[1]['first_time']+=np.timedelta64(12,'h')
            with self.subTest(mode=mode),self.assertRaises(ValueError): validate_sequence(cs,gs,2032,2059)
    def test_full_period_arithmetic_and_missing_year(self):
        cols=['precip_mm','log1p_precip_mm','cdd_max_days','rx5day_mm']+heat_basis_feature_names([29],3)
        a=pd.DataFrame(dict(crop=['mai']*28,lat=[39.25]*28,lon_360=[.25]*28,harvest_year=range(2032,2060),
            **{c:np.arange(28,dtype=float) for c in cols}))
        b=a.copy();b[cols]+=3
        r=compare(a,b,29,2032,2059)
        self.assertEqual(r['paired_crop_years'],28)
        self.assertTrue(all(v['equal_cell_mean']==3 for v in r['features'].values()))
        with self.assertRaises(ValueError):compare(a.iloc[:-1],b.iloc[:-1],29,2032,2059)
        with self.assertRaises(ValueError):compare(a,b,29)


if __name__=='__main__':unittest.main()

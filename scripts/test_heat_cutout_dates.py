"""Synthetic chronology tests. These data are never empirical products."""
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr
from heat_cutout_dates import date_contract, registered_years
from run_authorized_heat_subset_pilot import validate_cutout


class Dates(unittest.TestCase):
    def test_counts_and_bounds(self):
        self.assertEqual([date_contract(a,a+9)[2] for a in (2031,2041,2051)], [3653,3652,3653])
        for a,b in [(True,2050),(2050,2041),(1800,1801),(2041,2101),(2041.0,2050)]:
            with self.assertRaises(ValueError): date_contract(a,b)

    def test_source_registration(self):
        c=dict(file_name='x_2041_2050.nc',expected_gregorian_daily_count=3652)
        self.assertEqual(registered_years(c),(2041,2050))
        for changes in [dict(expected_start_year=2031),dict(expected_gregorian_daily_count=3653)]:
            with self.assertRaises(ValueError): registered_years(c|changes)

    def test_file_dates_leap_gap_and_duplicate(self):
        # Full registered spatial grid, one synthetic leap year, compressed on disk.
        dates=pd.date_range('2032-01-01','2032-12-31')
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'synthetic.nc'
            def write(times):
                ds=xr.Dataset({'tasmax':(('time','lat','lon'),np.full((len(times),2,720),290.,dtype='float32'),{'units':'K'})},
                    coords={'time':times,'lat':[39.75,39.25],'lon':np.arange(-179.75,180,.5)})
                ds.to_netcdf(path,engine='h5netcdf',encoding={'tasmax':{'zlib':True}})
            write(dates)
            self.assertEqual(validate_cutout(path,2032,2032)['days'],366)
            with self.assertRaises(ValueError): validate_cutout(path)
            write(dates.delete(59))
            with self.assertRaises(ValueError): validate_cutout(path,2032,2032)
            wrong=dates.to_numpy().copy();wrong[59]=wrong[58];write(wrong)
            with self.assertRaises(ValueError): validate_cutout(path,2032,2032)


if __name__=='__main__': unittest.main()

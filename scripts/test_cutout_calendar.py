"""Synthetic cutout/full-grid heat parity and exact-coordinate failure tests."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd
import xarray as xr

from align_cutout_calendar import align_calendar

SCRIPTS = Path(__file__).resolve().parent


def fixture():
    coords = {'lat': [40.25, 39.75, 39.25, 38.75], 'lon': [-.25, .25]}
    # Leap-year DOY 365 is Dec 30; Jan 3 harvest spans five daily values.
    calendar = xr.Dataset({
        'planting_day': (('lat', 'lon'), np.full((4, 2), 365.)),
        'maturity_day': (('lat', 'lon'), np.full((4, 2), 3.)),
    }, coords=coords)
    weather = xr.Dataset({'tasmax': (('time', 'lat', 'lon'),
        (np.arange(40).reshape(5, 4, 2) / 4 + 27 + 273.15), {'units': 'K'})},
        coords={'time': pd.date_range('2020-12-30 12:00', periods=5), **coords})
    return calendar, weather


class CutoutTests(unittest.TestCase):
    def test_exact_order_and_rejections(self):
        cal, full = fixture()
        cut = full.isel(lat=[2, 1], lon=[1, 0])
        selected = align_calendar(cal, cut.tasmax)
        np.testing.assert_array_equal(selected.lat, cut.lat)
        np.testing.assert_array_equal(selected.lon, cut.lon)
        for bad in (cut.assign_coords(lat=[39.25001, 39.75]),
                    cut.assign_coords(lat=[39.25, 39.25]),
                    cut.assign_coords(lon=[np.nan, -.25])):
            with self.assertRaises(ValueError):
                align_calendar(cal, bad.tasmax)
        with self.assertRaises(ValueError):
            align_calendar(cal.assign_coords(lon=[.25, .25]), cut.tasmax)
        with self.assertRaises(ValueError):
            align_calendar(cal.transpose('lon', 'lat'), cut.tasmax)

    def test_full_grid_and_cutout_builders_match(self):
        cal, full = fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cal.to_netcdf(root/'calendar.nc', engine='h5netcdf')
            full.to_netcdf(root/'full.nc', engine='h5netcdf')
            full.isel(lat=slice(1, 3)).to_netcdf(root/'cut.nc', engine='h5netcdf')
            for builder in ('build_crop_heat_features.py', 'build_crop_stage_heat_features.py'):
                frames = []
                for name, start, stop, extra in (('full', '1', '3', []),
                        ('cut', '0', '2', ['--calendar-by-coordinates'])):
                    out = root/f'{builder}_{name}.parquet'
                    subprocess.run([sys.executable, str(SCRIPTS/builder),
                        '--tasmax', str(root/f'{name}.nc'), '--calendar', str(root/'calendar.nc'),
                        '--crop', 'maize', '--irrigation', 'noirr',
                        '--year-start', '2021', '--year-end', '2021',
                        '--lat-start', start, '--lat-stop', stop,
                        '--threshold-c', '29', '--threshold-c', '30',
                        '--out', str(out), *extra], check=True)
                    frames.append(pd.read_parquet(out))
                pd.testing.assert_frame_equal(*frames, check_exact=True)
                self.assertTrue(frames[0].cross_year.all())
                if 'stage_days' in frames[0]:
                    self.assertEqual(len(frames[0]), 12)
                    self.assertTrue((frames[0].groupby(['lat','lon']).stage_days.sum()==5).all())
                else:
                    self.assertEqual(len(frames[0]), 4)
                    self.assertTrue((frames[0].season_days==5).all())


if __name__ == '__main__':
    unittest.main()

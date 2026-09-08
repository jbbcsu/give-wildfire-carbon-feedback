"""Synthetic variable validation and direct-weather cutout parity only."""
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
import xarray as xr
from run_authorized_heat_subset_pilot import validate_cutout
from test_cutout_calendar import fixture,SCRIPTS


class HistoricalCutouts(unittest.TestCase):
    def test_variable_units_negatives_and_identity(self):
        coords=dict(time=pd.date_range('1981-01-01',periods=365),lat=[39.75,39.25],lon=np.arange(-179.75,180,.5))
        def dataset(var,value,units):
            return xr.Dataset({var:(('time','lat','lon'),np.full((365,2,720),value),{'units':units})},coords=coords)
        for var,value,units,key,expected in [('pr',1/86400,'kg m-2 s-1','minimum_mm_day',1),
            ('pr',2,'mm/day','minimum_mm_day',2),('tas',290,'K','minimum_c',16.85)]:
            with patch('run_authorized_heat_subset_pilot.xr.open_dataset',return_value=dataset(var,value,units)):
                self.assertAlmostEqual(validate_cutout(Path('SYNTHETIC'),1981,1981,variable=var)[key],expected)
        for ds,var in [(dataset('pr',-1,'mm/day'),'pr'),(dataset('pr',1,'K'),'pr'),
                       (dataset('tas',290,'K'),'tasmax')]:
            with patch('run_authorized_heat_subset_pilot.xr.open_dataset',return_value=ds),self.assertRaises(ValueError):
                validate_cutout(Path('SYNTHETIC'),1981,1981,variable=var)
        with self.assertRaises(ValueError):validate_cutout(Path('SYNTHETIC'),1981,1981,variable='unknown')

    def test_direct_weather_full_cutout_parity_and_grid_rejection(self):
        calendar,full=fixture()
        full=full.rename(tasmax='tas')
        full['pr']=xr.DataArray(np.arange(40).reshape(5,4,2)/10,dims=('time','lat','lon'),attrs={'units':'mm/day'})
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);calendar.to_netcdf(root/'calendar.nc',engine='h5netcdf')
            for name,ds in [('full',full),('cut',full.isel(lat=slice(1,3)))]:
                ds[['pr']].to_netcdf(root/f'{name}_pr.nc',engine='h5netcdf')
                ds[['tas']].to_netcdf(root/f'{name}_tas.nc',engine='h5netcdf')
            full.isel(lat=slice(1,3))[['tas']].assign_coords(lon=[-.24,.26]).to_netcdf(root/'bad_tas.nc',engine='h5netcdf')
            for script in ('build_crop_year_features.py','build_crop_stage_features.py'):
                frames=[]
                def command(name,start,stop,extra,tempfile=None):
                    return [sys.executable,str(SCRIPTS/script),'--precip',str(root/f'{name}_pr.nc'),
                        '--temperature',str(tempfile or root/f'{name}_tas.nc'),'--calendar',str(root/'calendar.nc'),
                        '--crop','mai','--irrigation','noirr','--year-start','2021','--year-end','2021',
                        '--lat-start',start,'--lat-stop',stop,'--out',str(root/f'{script}_{name}_{bool(tempfile)}.parquet'),*extra]
                for name,start,stop,extra in [('full','1','3',[]),('cut','0','2',['--calendar-by-coordinates'])]:
                    subprocess.run(command(name,start,stop,extra),check=True,capture_output=True)
                    frames.append(pd.read_parquet(root/f'{script}_{name}_False.parquet'))
                pd.testing.assert_frame_equal(*frames,check_exact=True)
                self.assertTrue(frames[0].cross_year.all())
                bad=subprocess.run(command('cut','0','2',['--calendar-by-coordinates'],root/'bad_tas.nc'),capture_output=True,text=True)
                self.assertNotEqual(bad.returncode,0);self.assertIn('axes differ',bad.stderr)


if __name__=='__main__':unittest.main()

"""Synthetic-only safety/content tests. Never calls any network endpoint."""
import io
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import numpy as np
import pandas as pd
import xarray as xr

import run_authorized_heat_subset_pilot as pilot


class Archive:
    def __init__(self,infos):self.infos=infos
    def infolist(self):return self.infos


def member(name='folder/data.nc',size=100):
    info=zipfile.ZipInfo(name);info.file_size=size
    info.external_attr=(stat.S_IFREG|0o600)<<16
    return info


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.no_network=patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('network forbidden in tests'))
        self.no_network.start();self.addCleanup(self.no_network.stop)

    def test_authorization_fail_closed(self):
        # This synthetic format check is not a user authorization record.
        good=dict(scope='one_isimip_heat_cutout_pilot',additional_disk_budget_bytes=pilot.BUDGET,
            config_sha256='synthetic-hash',job_id='synthetic-job',user_approved=True,
            user_approval_quote='SYNTHETIC ONLY; NOT ACTUAL USER APPROVAL',
            approved_at_iso='2026-09-07T00:00:00+00:00')
        pilot.validate_authorization(good,'synthetic-hash','synthetic-job')
        for update in ({'user_approved':False},{'user_approved':1},{'additional_disk_budget_bytes':2*pilot.BUDGET},
                       {'user_approval_quote':''},{'job_id':'different'},
                       {'config_sha256':'different'},{'approved_at_iso':'2026-09-07T00:00:00'}):
            with self.assertRaises(ValueError):
                pilot.validate_authorization({**good,**update},'synthetic-hash','synthetic-job')

    def test_stream_exact_and_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);calls=[]
            payload=b'x'*(pilot.CHUNK+17)
            digest=pilot.stream_copy(io.BytesIO(payload),root/'valid',len(payload),calls.append)
            self.assertEqual(digest,pilot.hashlib.sha256(payload).hexdigest())
            self.assertLessEqual(max(calls),pilot.CHUNK)
            for name,data,size in [('short',b'xx',3),('long',b'xxxx',3)]:
                with self.assertRaises(ValueError):
                    pilot.stream_copy(io.BytesIO(data),root/name,size,lambda _:None)
                self.assertTrue((root/name).exists())
            with self.assertRaises(FileExistsError):
                pilot.stream_copy(io.BytesIO(payload),root/'valid',len(payload),calls.append)
            with self.assertRaises(ValueError):
                pilot.stream_copy(io.BytesIO(b'a'),root/'budget',1,
                                  lambda _:(_ for _ in ()).throw(ValueError('budget')))
            self.assertEqual((root/'budget').stat().st_size,0)

    def test_archive_paths_types_and_budgets(self):
        self.assertEqual(pilot.inspect_archive(Archive([member()]),100).filename,'folder/data.nc')
        link=member();link.external_attr=(stat.S_IFLNK|0o777)<<16
        encrypted=member();encrypted.flag_bits=1
        for infos in ([member('../data.nc')],[member('/data.nc')],
                      [member('C:\\data.nc')],[link],[encrypted],
                      [member(),member()],[member('unexpected.exe')],
                      [member(size=pilot.BUDGET)],[member(size=0)],
                      [member(),member('sidecar.json',2**20+1)]):
            with self.assertRaises(ValueError):pilot.inspect_archive(Archive(infos),100)

    def test_cutout_content_contract(self):
        values=np.full((3652,2,720),300.,dtype=np.float32)
        ds=xr.Dataset({'tasmax':(('time','lat','lon'),values,{'units':'K'})},coords={
            'time':pd.date_range('2041-01-01 12:00',periods=3652),
            'lat':[39.75,39.25],'lon':np.arange(-179.75,180.,.5)})
        with patch.object(pilot.xr,'open_dataset',return_value=ds):
            result=pilot.validate_cutout(Path('SYNTHETIC_NOT_A_REAL_FILE'))
        self.assertEqual(result['days'],3652)
        self.assertAlmostEqual(result['minimum_c'],26.85,places=4)
        for bad in (ds.isel(lat=[0]),ds.isel(time=slice(1,None)),
                    ds.assign_coords(lon=ds.lon.values+.01),ds.rename(tasmax='tas')):
            with patch.object(pilot.xr,'open_dataset',return_value=bad),self.assertRaises(ValueError):
                pilot.validate_cutout(Path('SYNTHETIC_NOT_A_REAL_FILE'))
        values[0,0,0]=np.nan
        with patch.object(pilot.xr,'open_dataset',return_value=ds),self.assertRaises(ValueError):
            pilot.validate_cutout(Path('SYNTHETIC_NOT_A_REAL_FILE'))


if __name__=='__main__':unittest.main()

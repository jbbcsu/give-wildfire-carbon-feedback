import copy
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr
from prepare_us_paired_regional_cutout import ROOT, BANDS, PROTOCOL, sha256, parent_and_payload
from acquire_registered_heat_cutout import check_archive_identity
from validate_us_paired_regional_cutout import validate


class RegionTests(unittest.TestCase):
    def config(self):
        path = ROOT/'config/isimip3a_counterclim_pr_1981_cutout_20260908.json'
        return dict(role='registered_us_paired_regional_climate_request', band='central',
            bbox_west_east_south_north=BANDS['central'], parent_source_config=str(path.relative_to(ROOT)),
            parent_source_config_sha256=sha256(path), protocol_sha256=sha256(ROOT/PROTOCOL),
            source_averaging_authorized=False, damage_or_scc_authorized=False)

    def test_payload_uses_new_region_not_parent(self):
        parent, payload = parent_and_payload(self.config())
        self.assertEqual(parent['bbox_west_east_south_north'], [-180, 180, 39, 40])
        self.assertEqual(payload['operations'][0]['bbox'], BANDS['central'])
        self.assertFalse(payload['operations'][0]['compute_mean'])

    def test_changed_contract(self):
        for field, value in [('bbox_west_east_south_north', [-180, 180, -90, 90]),
                             ('parent_source_config_sha256', 'changed'), ('damage_or_scc_authorized', True),
                             ('protocol_sha256', 'changed')]:
            c = copy.deepcopy(self.config())
            c[field] = value
            with self.assertRaises(ValueError):
                parent_and_payload(c)

    def test_archive_cap_and_host(self):
        url = 'https://files.isimip.org/api/v2/output/isimip-download-example.zip'
        check_archive_identity(url, 'example', 1, 'etag')
        for u, size in [(url, 17*2**20), ('https://invalid.example/file.zip', 1)]:
            with self.assertRaises(ValueError):
                check_archive_identity(u, 'example', size, 'etag')

    def test_regional_daily_validation(self):
        config = self.config()
        parent = ROOT/'config/isimip3a_obsclim_pr_1981_cutout_20260908.json'
        config.update(parent_source_config=str(parent.relative_to(ROOT)), parent_source_config_sha256=sha256(parent))
        ds = xr.Dataset({'pr': (('time', 'lat', 'lon'), np.full((3652, 16, 70), 1/86400, dtype='float32'),
                                {'units': 'kg m-2 s-1'})},
                        coords={'time': pd.date_range('1981-01-01', '1990-12-31'),
                                'lat': np.arange(41.25, 33.5, -.5), 'lon': np.arange(-109.25, -74.5, .5)})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'synthetic_factual.nc'
            ds.to_netcdf(path, engine='h5netcdf')
            result = validate(path, config)
            self.assertEqual((result['days'], result['finite_cells']), (3652, 1120))
            ds['pr'].values[0, 0, 0] = np.nan
            ds.to_netcdf(path, engine='h5netcdf')
            with self.assertRaisesRegex(ValueError, 'nonfinite factual'):
                validate(path, config)
            ds = ds.isel(time=slice(1, None))
            ds.to_netcdf(path, engine='h5netcdf')
            with self.assertRaisesRegex(ValueError, 'chronology'):
                validate(path, config)


if __name__ == '__main__':
    unittest.main()

"""Synthetic metadata and non-download gate tests only."""
import copy
import unittest
from prepare_heat_subset_pilot import validate_and_prepare


def fixture():
    config=dict(local_download_authorized=False,local_feature_construction_authorized=False,
        damage_or_scc_authorized=False,dataset_id='synthetic-dataset',dataset_version='v1',
        resource_doi='synthetic-doi',file_id='synthetic-file',file_name='fake.nc',source_path='fake/path/fake.nc',
        source_bytes=10,source_sha512='0'*128,specifiers={'climate_variable':'tasmax'},
        bbox_west_east_south_north=[-180,180,39,40])
    dataset=dict(id='synthetic-dataset',version='v1',public=True,restricted=False,rights={'short':'CC0 1.0'},
        resources=[{'doi':'synthetic-doi'}],specifiers={'climate_variable':'tasmax'},
        files=[dict(id='synthetic-file',name='fake.nc',path='fake/path/fake.nc',version='v1',size=10,
                    checksum='0'*128,checksum_type='sha512')])
    return config,dataset


class TestSubset(unittest.TestCase):
    def test_single_exact_path_and_no_averaging(self):
        config,dataset=fixture();p=validate_and_prepare(config,dataset)
        self.assertEqual(p['paths'],['fake/path/fake.nc'])
        self.assertEqual(p['operations'],[dict(operation='select_bbox',bbox=[-180,180,39,40],compute_mean=False,output_csv=False)])

    def test_closed_gates_and_wrong_source(self):
        for change in ('gate','bbox','rights','checksum','member','duplicate'):
            config,dataset=fixture()
            if change=='gate':config['local_download_authorized']=True
            if change=='bbox':config['bbox_west_east_south_north']=[-180,180,-90,90]
            if change=='rights':dataset['rights']['short']='restricted'
            if change=='checksum':dataset['files'][0]['checksum']='1'*128
            if change=='member':dataset['specifiers']['climate_variable']='tas'
            if change=='duplicate':dataset['files'].append(copy.deepcopy(dataset['files'][0]))
            with self.subTest(change=change),self.assertRaises(ValueError):validate_and_prepare(config,dataset)


if __name__=='__main__':unittest.main()

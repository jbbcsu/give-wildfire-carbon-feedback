"""Source-contract validation only; no model/observation results."""
import copy
import json
from pathlib import Path
import unittest
from build_historical_climate_benchmark import validate_contracts

class HistoricalContract(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[1]
        self.configs=[json.loads((root/f'config/isimip3b_gfdl_historical_{v}_{a}_cutout_20260908.json').read_text())
            for v in ('pr','tas','tasmax') for a in (1981,1991,2001)]
    def test_registered_sources(self):validate_contracts(self.configs)
    def test_independent_ipsl_and_cross_model_rejection(self):
        root=Path(__file__).resolve().parents[1]
        ipsl=[json.loads((root/f'config/isimip3b_ipsl_historical_{v}_{a}_cutout_20260908.json').read_text())
            for v in ('pr','tas','tasmax') for a in (1981,1991,2001)]
        validate_contracts(ipsl,'ipsl')
        for configs,model in ((ipsl,'gfdl'),(self.configs,'ipsl'),(ipsl,'other')):
            with self.assertRaises(ValueError):validate_contracts(configs,model)
        relabeled=copy.deepcopy(self.configs)
        for c in relabeled:c['specifiers']['climate_forcing']='ipsl-cm6a-lr'
        with self.assertRaises(ValueError):validate_contracts(relabeled,'ipsl')
    def test_missing_duplicate_wrong_realization_or_dataset(self):
        for mode in ('missing','duplicate','future','member','version','dataset','period'):
            configs=copy.deepcopy(self.configs)
            if mode=='missing':configs.pop()
            if mode=='duplicate':configs.append(configs[0])
            if mode=='future':configs[0]['specifiers']['climate_scenario']='ssp126'
            if mode=='member':configs[0]['specifiers']['ensemble_member']='r2i1p1f1'
            if mode=='version':configs[0]['dataset_version']='other'
            if mode=='dataset':configs[0]['dataset_id']='other'
            if mode=='period':configs[0]['expected_start_year']=1982
            with self.subTest(mode=mode),self.assertRaises(ValueError):validate_contracts(configs)

if __name__=='__main__':unittest.main()

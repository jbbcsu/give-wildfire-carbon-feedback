"""Registered real-source metadata tests; no synthetic data presented as evidence."""
import copy
import json
from pathlib import Path
import unittest
from build_observational_climate_benchmark import validate_contracts


class ObservationalContract(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[1]
        self.configs={s:[json.loads((root/f'config/isimip3a_{s}_{v}_{a}_cutout_20260908.json').read_text())
            for v in ('pr','tas','tasmax') for a in (1981,1991,2001)] for s in ('obsclim','counterclim')}
    def test_registered_pairs(self):
        for s,configs in self.configs.items():validate_contracts(configs,s)
    def test_wrong_source_or_relabeling(self):
        with self.assertRaises(ValueError):validate_contracts(self.configs['obsclim'],'counterclim')
        relabeled=copy.deepcopy(self.configs['obsclim'])
        for c in relabeled:c['specifiers']['climate_scenario']='counterclim'
        with self.assertRaises(ValueError):validate_contracts(relabeled,'counterclim')
        for field,value in [('dataset_version','20211021'),('resource_doi','other'),('dataset_id','other')]:
            c=copy.deepcopy(self.configs['counterclim']);c[0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):validate_contracts(c,'counterclim')
    def test_missing_duplicate_model_and_period(self):
        for mode in ('missing','duplicate','model','period'):
            c=copy.deepcopy(self.configs['counterclim'])
            if mode=='missing':c.pop()
            if mode=='duplicate':c.append(c[0])
            if mode=='model':c[0]['specifiers']['climate_forcing']='gfdl-esm4'
            if mode=='period':c[0]['expected_start_year']=1982
            with self.subTest(mode=mode),self.assertRaises(ValueError):validate_contracts(c,'counterclim')


if __name__=='__main__':unittest.main()

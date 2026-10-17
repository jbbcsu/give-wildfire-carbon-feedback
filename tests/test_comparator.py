import csv,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TestComparator(unittest.TestCase):
 def setUp(self):self.cfg=json.loads((ROOT/'config/macro_comparator_v1.json').read_text())
 def test_mutually_exclusive(self):self.assertFalse(self.cfg['scope']['additive_to_give']);self.assertFalse(self.cfg['scope']['omitted_sector_residual'])
 def test_comparability_closed(self):self.assertFalse(any(self.cfg['comparability_gates'].values()))
 def test_source_rows(self):
  with (ROOT/self.cfg['source']['result_file']).open(newline='') as f:r=list(csv.DictReader(f))
  p=[x for x in r if x['Year']=='2024' and x['Data']=='PWT' and x['Temperature']=='global'];self.assertEqual(len(p),1);self.assertAlmostEqual(float(p[0]['SCC']),1206.96927919086)
 def test_forbidden_residual_claim(self):self.assertIn('omitted-sector residual',self.cfg['forbidden_claims'])
if __name__=='__main__':unittest.main()

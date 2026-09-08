"""Synthetic tests only; no empirical climate/yield damages."""
import json
import math
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.anticipated_weather_market import market_response
from src.constant_elasticity_market import Market,equilibrium

class TestMarket(unittest.TestCase):
    def setUp(self):
        self.kw=dict(supply_elasticity=.1,demand_elasticity_magnitude=.04,
                     expected_log_supply_ratio=math.log(.99),realized_log_supply_ratio=math.log(.98),price_shrinkage=.39)
    def test_direct_equations(self):
        r=market_response(**self.kw);p=.99**(-1/.14);q=p**(-.04)
        raw_q=q*.98/.99;raw_p=raw_q**(-1/.04);final_p=.61*raw_p+.39*p
        for name,value in [('expected_price_ratio',p),('raw_quantity_ratio',raw_q),('raw_price_ratio',raw_p),('final_price_ratio',final_p),('final_quantity_ratio',final_p**(-.04))]:
            self.assertTrue(math.isclose(r[name],value,rel_tol=1e-13),name)
        self.assertFalse(r['welfare_computed']);self.assertFalse(r['causal_or_scc_result'])
    def test_anticipated_core_limit(self):
        specs=json.loads((ROOT/'config/hultgren_k6_market_scenarios_20260908.json').read_text())
        for s in specs['scenarios']:
            e=s['supply_elasticity'];d=-s['signed_demand_elasticity']
            for a in (-.1,0.,.1):
                reference=equilibrium(Market(e,d,1.,'normalized'),a)
                for shrink in (0.,.39,1.):
                    r=market_response(supply_elasticity=e,demand_elasticity_magnitude=d,expected_log_supply_ratio=a,realized_log_supply_ratio=a,price_shrinkage=shrink)
                    self.assertTrue(math.isclose(r['final_price_ratio'],reference['price_ratio'],rel_tol=1e-14))
                    self.assertTrue(math.isclose(r['final_quantity_ratio'],reference['quantity_ratio'],rel_tol=1e-14))
    def test_storage_endpoints_and_order(self):
        for b in (math.log(.98),math.log(1.01)):
            kw=self.kw|dict(realized_log_supply_ratio=b)
            raw=market_response(**(kw|dict(price_shrinkage=0)))
            full=market_response(**(kw|dict(price_shrinkage=1)))
            middle=market_response(**kw)
            self.assertEqual(raw['final_price_ratio'],raw['raw_price_ratio'])
            self.assertEqual(full['final_price_ratio'],full['expected_price_ratio'])
            self.assertLessEqual(min(raw['final_price_ratio'],full['final_price_ratio']),middle['final_price_ratio'])
            self.assertLessEqual(middle['final_price_ratio'],max(raw['final_price_ratio'],full['final_price_ratio']))
    def test_invalid_and_extreme(self):
        for field,value in [('supply_elasticity',0),('demand_elasticity_magnitude',-.04),('price_shrinkage',1.1),('expected_log_supply_ratio',float('nan')),('price_shrinkage',True),('realized_log_supply_ratio',-1000)]:
            with self.assertRaises(ValueError):market_response(**(self.kw|{field:value}))

if __name__=='__main__':unittest.main()

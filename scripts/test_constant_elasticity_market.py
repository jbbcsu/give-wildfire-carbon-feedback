"""Synthetic theory checks only. No empirical calibration or damage estimate."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from constant_elasticity_market import Market, equilibrium, paired_surplus, productivity_to_supply


def integrate(function, left, right, n=4096):
    width = (right-left)/n
    return width/3*(function(left)+function(right)+sum(
        (4 if i%2 else 2)*function(left+i*width) for i in range(1, n)))


class MarketTests(unittest.TestCase):
    def test_zero_and_market_clearing(self):
        for es in (.2, .5, 1., 2.):
            for ed in (.1, .5, 1., 2.):
                market = Market(es, ed, 100., 'synthetic_value_units')
                zero = equilibrium(market, 0)
                self.assertEqual(zero['total_surplus_change'], 0)
                self.assertEqual(zero['price_ratio'], 1)
                for shock in (-.2, .2):
                    fit = equilibrium(market, shock)
                    self.assertAlmostEqual(math.exp(shock)*fit['price_ratio']**es,
                                           fit['price_ratio']**-ed, places=12)
                    self.assertGreater(fit['total_surplus_change']*shock, 0)
                    self.assertAlmostEqual(fit['consumer_surplus_change']+
                                           fit['producer_surplus_change'],
                                           fit['total_surplus_change'], places=11)

    def test_independent_surplus_integrals(self):
        for es in (.5, 1.):
            for ed in (.2, 1., 2.):
                market = Market(es, ed, 100., 'synthetic_value_units')
                for shock in (-.1, .1):
                    fit = equilibrium(market, shock)
                    p, q = fit['price_ratio'], fit['quantity_ratio']
                    cs = -100*integrate(lambda price: price**-ed, 1, p)
                    before_cost = integrate(lambda quantity: quantity**(1/es), 0, 1)
                    after_cost = integrate(lambda quantity: (quantity/math.exp(shock))**(1/es), 0, q)
                    ps = 100*(p*q-after_cost-1+before_cost)
                    self.assertAlmostEqual(fit['consumer_surplus_change'], cs, places=9)
                    self.assertAlmostEqual(fit['producer_surplus_change'], ps, places=9)

    def test_unit_elastic_demand_limit(self):
        center = equilibrium(Market(.5, 1., 100., 'synthetic'), .1)
        self.assertEqual(center['producer_surplus_change'], 0)
        for ed in (1-1e-12, 1+1e-12):
            near = equilibrium(Market(.5, ed, 100., 'synthetic'), .1)
            self.assertAlmostEqual(near['total_surplus_change'], center['total_surplus_change'], places=10)

    def test_tiny_increment_and_centered_convergence(self):
        market = Market(.5, .3, 100., 'synthetic')
        base = .15
        exact = paired_surplus(market, base, 0)['derivative_total_surplus_wrt_log_supply_at_baseline']
        errors = []
        for step in (1e-2, 1e-3, 1e-4):
            plus = paired_surplus(market, base, step)['total_surplus_change']
            minus = paired_surplus(market, base, -step)['total_surplus_change']
            errors.append(abs((plus-minus)/(2*step)-exact))
        self.assertTrue(errors[2] < errors[1] < errors[0])
        tiny = paired_surplus(market, base, 1e-15)['total_surplus_change']
        self.assertAlmostEqual(tiny/1e-15, exact, places=10)

    def test_pair_matches_levels_and_unit_scaling(self):
        market = Market(.7, .4, 100., 'synthetic')
        pair = paired_surplus(market, .1, -.03)
        base, after = equilibrium(market, .1), equilibrium(market, .07)
        for name in ('consumer_surplus_change', 'producer_surplus_change', 'total_surplus_change'):
            self.assertAlmostEqual(pair[name], after[name]-base[name], places=11)
        double = paired_surplus(Market(.7, .4, 200., 'synthetic'), .1, -.03)
        self.assertAlmostEqual(double['total_surplus_change'], 2*pair['total_surplus_change'])

    def test_shock_mapping_is_not_implicit(self):
        s = productivity_to_supply(.1, .5, convention='horizontal_output')
        t = productivity_to_supply(.1, .5, convention='fixed_input_cost')
        self.assertAlmostEqual(s, .1)
        self.assertAlmostEqual(t, .15)
        with self.assertRaises(ValueError):
            productivity_to_supply(.1, .5, convention='automatic')

    def test_invalid_inputs(self):
        for args in ((0, 1, 1, 'u'), (1, -1, 1, 'u'), (1, 1, 0, 'u'),
                     (1, 1, 1, ''), (math.nan, 1, 1, 'u')):
            with self.assertRaises(ValueError):
                Market(*args)
        market = Market(.5, .2, 1, 'synthetic')
        for shock in (math.nan, math.inf, 1e6, -1e6):
            with self.assertRaises(ValueError):
                equilibrium(market, shock)
            with self.assertRaises(ValueError):
                paired_surplus(market, shock, .01)


if __name__ == '__main__':
    unittest.main()

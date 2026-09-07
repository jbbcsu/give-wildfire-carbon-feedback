"""Synthetic rounding and economic-state tests, not empirical evidence."""
import copy
import unittest
from evaluate_normalized_welfare_sensitivity import rounded_multiplier_check,evaluate


def synthetic_config():
    return dict(production_calibration_authorized=False,damage_or_scc_authorized=False,
        source_rounding_decimals=3,multiplier_rounding_decimals=2,
        columns=[dict(id=k,supply=.2,demand_signed=-.1,printed_multiplier=3.33)
                 for k in ['1a','1b','1c','2a','2b','2c']])


class TestNormalized(unittest.TestCase):
    def test_rounding_interval_and_bad_pair(self):
        self.assertTrue(rounded_multiplier_check(.2,-.1,3.33)['rounding_consistent'])
        with self.assertRaises(ValueError): rounded_multiplier_check(.2,-.1,4.)
        with self.assertRaises(ValueError): rounded_multiplier_check(.2,.1,10.)

    def test_hypothetical_matrix_and_mapping(self):
        result=evaluate(synthetic_config())
        self.assertEqual(len(result['states']),36)
        for r in result['states']:
            ds_dloga=1.2 if r['convention']=='fixed_input_cost' else 1.
            expected_local=r['price_ratio']**.9/1.2*ds_dloga
            self.assertAlmostEqual(r['local_surplus_derivative_wrt_log_productivity'],expected_local)
            if r['hypothetical_productivity_factor']==1.:
                self.assertEqual(r['price_ratio'],1.)
                self.assertEqual(r['damage_fraction'],0.)
                expected=1. if r['convention']=='fixed_input_cost' else 1/1.2
                self.assertAlmostEqual(r['local_surplus_derivative_wrt_log_productivity'],expected)
            elif r['hypothetical_productivity_factor']<1.:
                self.assertGreater(r['price_ratio'],1.)
                self.assertGreater(r['damage_fraction'],0.)
            else:
                self.assertLess(r['damage_fraction'],0.)

    def test_no_gate_or_source_subset_promotion(self):
        config=synthetic_config();config['damage_or_scc_authorized']=True
        with self.assertRaises(ValueError): evaluate(config)
        config=synthetic_config();config['columns'].pop()
        with self.assertRaises(ValueError): evaluate(config)


if __name__=='__main__':
    unittest.main()

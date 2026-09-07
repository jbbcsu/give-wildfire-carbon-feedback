"""Synthetic quadratic contrast and covariance tests, no empirical fixtures."""
import unittest
import numpy as np
from summarize_rainfall_response_curves import rainfall_curve,range_support


class TestCurves(unittest.TestCase):
    def test_direct_polynomial_and_full_covariance(self):
        beta=np.array([.03,-.002]);cov=np.array([[.0004,-.00001],[-.00001,.000003]])
        rain=np.array([100.,300.,900.]);reference=500.
        curves=rainfall_curve(beta,cov,rain,reference)
        for p,row in zip(rain/100,curves):
            p0=reference/100
            expected=(beta[0]*p+beta[1]*p*p)-(beta[0]*p0+beta[1]*p0*p0)
            g1,g2=p-p0,p*p-p0*p0
            variance=g1*g1*cov[0,0]+2*g1*g2*cov[0,1]+g2*g2*cov[1,1]
            self.assertAlmostEqual(row['log_yield_contrast'],expected)
            self.assertAlmostEqual(row['standard_error_log_contrast']**2,variance)
            self.assertAlmostEqual(row['fitted_percent_difference'],100*np.expm1(expected))

    def test_reference_is_exact_zero(self):
        row=rainfall_curve([.1,-.001],np.eye(2),[527.3],527.3)[0]
        self.assertEqual(row['log_yield_contrast'],0.)
        self.assertEqual(row['standard_error_log_contrast'],0.)
        self.assertEqual(row['pointwise_ci95_percent'],[0.,0.])

    def test_reverse_sign_and_variance(self):
        a=rainfall_curve([.1,-.001],np.eye(2)*1e-5,[200],400)[0]
        b=rainfall_curve([.1,-.001],np.eye(2)*1e-5,[400],200)[0]
        self.assertAlmostEqual(a['log_yield_contrast'],-b['log_yield_contrast'])
        self.assertAlmostEqual(a['standard_error_log_contrast'],b['standard_error_log_contrast'])

    def test_invalid_inputs(self):
        for beta,cov,rain in [([1],np.eye(2),[1]),([1,2],[[1,2],[2,1]],[1]),
            ([1,2],[[1,0],[1,1]],[1]),([1,2],np.eye(2),[-1]),([1,np.nan],np.eye(2),[1])]:
            with self.subTest(),self.assertRaises(ValueError):
                rainfall_curve(beta,cov,rain,2)

    def test_county_range_requires_both_values(self):
        result=range_support([100,300,500],[400,600,900],200,350)
        self.assertEqual(result['counties_containing_both_values'],1)
        self.assertAlmostEqual(result['fraction_counties'],1/3)
        self.assertEqual(range_support([100,300,500],[400,600,900],700,350)['counties_containing_both_values'],0)


if __name__=='__main__':
    unittest.main()

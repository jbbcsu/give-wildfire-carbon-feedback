"""Synthetic absorption, direct-dummy and cluster-covariance checks only."""
import unittest
import numpy as np
from global_country_control_associations import absorb, absorbed_fit


class CountryTests(unittest.TestCase):
    def test_against_explicit_dummy_regression(self):
        rng = np.random.default_rng(70927)
        groups = np.repeat(np.arange(12),20)
        clusters = groups//3
        x, y = rng.normal(size=(240,3)), rng.normal(size=240)
        beta,cov,audit = absorbed_fit(x,y,groups,clusters)
        dummy = np.eye(12)[groups]
        full = np.column_stack([dummy,x])
        direct = np.linalg.lstsq(full,y,rcond=None)[0]
        residual = y-np.einsum('ni,i->n',full,direct,optimize=False)
        scores = [np.sum(full[clusters==g]*residual[clusters==g,None],axis=0)
                  for g in np.unique(clusters)]
        bread = np.linalg.inv(sum(np.outer(row,row) for row in full))
        meat = sum(np.outer(row,row) for row in scores)
        reference = (4/3)*(239/225)*np.einsum('ik,kl,lj->ij',bread,meat,bread,optimize=False)
        np.testing.assert_allclose(beta,direct[-3:],atol=1e-12)
        np.testing.assert_allclose(cov,reference[-3:,-3:],atol=1e-12)
        self.assertEqual(audit['residual_degrees_of_freedom'],225)

    def test_group_means_and_singletons(self):
        x = np.array([[1.],[3.],[9.]])
        y = np.array([3.,7.,8.])
        rx,ry,h,s = absorb(x,y,np.array([1,1,2]))
        np.testing.assert_allclose(rx.ravel(),[-1,1,0])
        np.testing.assert_allclose(ry,[-2,2,0])
        self.assertEqual((h,s),(2,1))

    def test_no_identifiable_variation(self):
        with self.assertRaises(ValueError):
            absorbed_fit(np.ones((10,2)),np.ones(10),np.arange(10),np.arange(10))


if __name__ == '__main__':
    np.seterr(invalid='raise',divide='raise',over='raise')
    unittest.main()

"""Synthetic domain validation; no synthetic climate result is exported."""
import unittest
import numpy as np
from validate_counterclim_crop_domain import validate_static_domain


class CropDomain(unittest.TestCase):
    def setUp(self):
        self.mask=np.array([[True,False],[False,True]])
        self.x=np.full((3,2,2),np.nan);self.x[:,self.mask]=1.
    def test_exact_static_noncrop_mask(self):
        self.assertEqual(validate_static_domain(self.x,self.mask),6)
    def test_any_crop_missing_or_infinite_rejected(self):
        for value in (np.nan,np.inf,-np.inf):
            x=self.x.copy();x[1,0,0]=value
            with self.subTest(value=value),self.assertRaises(ValueError):validate_static_domain(x,self.mask)
    def test_changed_intermittent_or_infinite_noncrop_rejected(self):
        for value in (0.,1.,np.inf):
            x=self.x.copy();x[1,0,1]=value
            with self.subTest(value=value),self.assertRaises(ValueError):validate_static_domain(x,self.mask)
        x=self.x.copy();x[:,0,1]=1
        with self.assertRaises(ValueError):validate_static_domain(x,self.mask)
    def test_invalid_domain_rejected(self):
        for mask in (self.mask.astype(int),np.zeros_like(self.mask),self.mask[:1]):
            with self.assertRaises(ValueError):validate_static_domain(self.x,mask)


if __name__=='__main__':unittest.main()

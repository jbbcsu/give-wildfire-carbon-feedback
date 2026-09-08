import unittest
import pandas as pd
from shapely.geometry import box
from inventory_us_paired_climate_overlap import coverage, paired_keys


class OverlapTests(unittest.TestCase):
    def test_geographic_classes(self):
        domain = box(0, 0, 2, 2)
        self.assertEqual(coverage(box(.1, .1, 1, 1), domain), 'full')
        self.assertEqual(coverage(box(1, 1, 3, 3), domain), 'partial')
        self.assertEqual(coverage(box(2, 0, 3, 1), domain), 'none')
        self.assertEqual(coverage(box(3, 3, 4, 4), domain), 'none')

    def test_missing_cell_hole(self):
        domain = box(0, 0, 3, 3).difference(box(1, 1, 2, 2))
        self.assertEqual(coverage(box(.5, .5, 2.5, 2.5), domain), 'partial')
        self.assertEqual(coverage(box(1.1, 1.1, 1.9, 1.9), domain), 'none')

    def test_practice_pairing(self):
        f = pd.DataFrame(dict(county_geoid=['20199'] * 2, outcome_crop=['corn_grain'] * 2,
                              harvest_year=[1982] * 2, irrigation_practice=['irrigated', 'non_irrigated']))
        self.assertEqual(len(paired_keys(f)), 1)
        for invalid in [f.iloc[:1], pd.concat([f, f.iloc[:1]])]:
            with self.assertRaises(ValueError):
                paired_keys(invalid)


if __name__ == '__main__':
    unittest.main()

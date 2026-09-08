import unittest
import pandas as pd
from compare_us_paired_county_climate import paired_summary


class ComparisonTests(unittest.TestCase):
    def frames(self):
        a = pd.DataFrame(dict(county_geoid=['a', 'a', 'b'], outcome_crop=['corn_grain']*3,
                              harvest_year=[1982, 1983, 1982], x=[2., 2., 8.]))
        b = a.copy()
        b['x'] = 0.
        return a, b

    def test_equal_county_not_equal_year(self):
        a, b = self.frames()
        result = paired_summary(a, b.iloc[::-1], ['x'])
        self.assertEqual(result['differences']['x']['equal_county_mean'], 5)
        self.assertEqual(result['differences']['x']['pooled_county_year_mean'], 4)

    def test_bad_keys_and_values(self):
        a, b = self.frames()
        bad = b.copy()
        bad.loc[0, 'x'] = float('nan')
        for invalid in [b.iloc[:2], pd.concat([b, b.iloc[:1]]), bad]:
            with self.assertRaises(ValueError):
                paired_summary(a, invalid, ['x'])


if __name__ == '__main__':
    unittest.main()

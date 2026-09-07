"""Synthetic coordinate and border fixtures; not empirical geography."""
import unittest
from build_mapspam_country_grid import half_degree_center, summarize_cells


class GridTests(unittest.TestCase):
    def test_centers_and_edges(self):
        self.assertEqual(half_degree_center(38.4583333333, 70.875), (38.25,70.75))
        self.assertEqual(half_degree_center(-89.9583333333,-179.9583333333),(-89.75,180.25))
        self.assertEqual(half_degree_center(89.9583333333,179.9583333333),(89.75,179.75))
        self.assertEqual(half_degree_center(-.0416666666667,-.0416666666667),(-.25,359.75))
        self.assertEqual(half_degree_center(.0416666666667,.0416666666667),(.25,.25))

    def test_invalid_coordinates(self):
        for lat,lon in ((90,0), (0,180), (float('nan'),0), (.1,.1)):
            with self.assertRaises(ValueError):
                half_degree_center(lat,lon)

    def test_no_majority_assignment(self):
        rows = summarize_cells({(.25,.25):({'AAA'},36),(.25,.75):({'AAA','BBB'},36)})
        self.assertEqual(rows[0]['country_label'],'AAA')
        self.assertIsNone(rows[1]['country_label'])
        with self.assertRaises(ValueError):
            summarize_cells({(.25,.25):({'AAA'},37)})


if __name__ == '__main__':
    unittest.main()

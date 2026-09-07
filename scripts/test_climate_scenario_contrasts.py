"""Synthetic climate pairing fixtures only; never projected/observed data."""
import unittest
import pandas as pd
from summarize_climate_scenario_contrasts import FEATURES,describe,pair_frames


def fixture():
    rows=[]
    for year in (2042,2043):
        for lon in (1.25,1.75):
            row=dict(year=year,lat=39.25,lon_360=lon,**{f:1. for f in FEATURES})
            row.update(precip_mm=100.,stage1_precip_share=.2,stage2_precip_share=.5,
                       stage3_precip_share=.3,precipitation_timing_centroid=.5,
                       precipitation_concentration_hhi=.1)
            rows.append(row)
    return pd.DataFrame(rows)


class ClimateTests(unittest.TestCase):
    def test_exact_contrast_and_pair_order(self):
        base=fixture()
        high=base.iloc[::-1].copy()
        high['precip_mm']+=20
        result=describe(base,high,[2042,2043])
        self.assertEqual(result['features']['precip_mm']['mean_difference'],20)
        self.assertEqual(result['features']['precip_mm']['percent_change_of_mean'],20)
        self.assertEqual(result['features']['stage1_precip_share']['mean_difference'],0)

    def test_incomplete_and_duplicate_support(self):
        base=fixture()
        for high in (base.iloc[:-1],pd.concat([base,base.iloc[:1]])):
            with self.assertRaises(ValueError):
                pair_frames(base,high,[2042,2043])

    def test_dry_shape_not_imputed(self):
        base,high=fixture(),fixture()
        high.loc[0,['precip_mm','stage1_precip_share','stage2_precip_share','stage3_precip_share']]=0
        result=describe(base,high,[2042,2043])
        self.assertEqual(result['shape_excluded_cells'],1)
        self.assertEqual(result['features']['precip_mm']['cells'],2)
        self.assertEqual(result['features']['stage1_precip_share']['cells'],1)
        self.assertEqual(result['candidate_zero_rain_cell_years'],1)

    def test_invalid_composition(self):
        base=fixture()
        bad=base.copy()
        bad.loc[0,'stage1_precip_share']=.8
        with self.assertRaises(ValueError):
            pair_frames(base,bad,[2042,2043])


if __name__=='__main__':
    unittest.main()

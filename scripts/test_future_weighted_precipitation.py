"""Synthetic algebra and fail-closed checks for future climate inputs."""
import unittest
import numpy as np
import pandas as pd
from build_future_weighted_precipitation import (
    weighted_climate, contrasts, join_season_stages, FEATURES, ZERO,
)


def fixture():
    rows=[]; weights=[]
    for regime, rain, shares, weight in (
            ('noirr',100.,[.6,.3,.1],.75),('firr',300.,[.1,.3,.6],.25)):
        row=dict(harvest_year=2000,lat=39.25,lon_360=20.25,crop='mai',irrigation=regime,
            yield_observed=False,yield_t_ha=np.nan,season_days=100,tmean_c=20.,
            precip_mm=rain,wet_days_n=30,cdd_max_days=20,rx1day_mm=rain*.1,
            rx5day_mm=rain*.3,wet_day_threshold_mm=1.)
        for i,(share,days) in enumerate(zip(shares,[30,40,30]),1):
            for name,value in dict(stage_days=days,tmean_c=20.,precip_mm=rain*share,
                    wet_days_n=10,cdd_max_days=10,rx1day_mm=rain*share/2,
                    rx5day_mm=rain*share).items():
                row[f'stage{i}_{name}']=value
        rows.append(row)
        weights.append(dict(lat=39.25,lon_360=20.25,crop='mai',irrigation=regime,
            area_share=weight,weight_source_id='synthetic',weight_vintage='fixed_2000',
            source_role='independent_fixed_baseline_crop_area_share',
            production_eligible=True,season_specific_share=True))
    return pd.DataFrame(rows),pd.DataFrame(weights)


class FutureTests(unittest.TestCase):
    def test_order_and_no_outcomes(self):
        panel,weights=fixture()
        out,audit=weighted_climate(panel,weights)
        row=out.iloc[0]
        self.assertAlmostEqual(row.precip_mm,150.)
        self.assertAlmostEqual(row.log1p_precip_mm,.75*np.log1p(100)+.25*np.log1p(300))
        self.assertAlmostEqual(row.stage1_precip_share,.475)
        self.assertAlmostEqual(row.precipitation_concentration_hhi,.46)
        self.assertGreater(audit['jensen_gap_mean'],0.)
        self.assertNotIn('yield_t_ha',out)
        self.assertNotIn('yield_observed',out)
        self.assertFalse(audit['future_outcomes_present'])

    def test_invalid_inputs(self):
        panel,weights=fixture()
        for bad in (pd.concat([panel,panel.iloc[:1]]),panel.iloc[:1],
                    panel.assign(yield_observed=True,yield_t_ha=1.)):
            with self.assertRaises(ValueError):weighted_climate(bad,weights)
        with self.assertRaises(ValueError):
            weighted_climate(panel,weights.assign(area_share=.2))

    def test_scenario_pairing_and_shape_exclusion(self):
        panel,weights=fixture();base,_=weighted_climate(panel,weights)
        candidate=base.copy();candidate['precip_mm']+=10
        got=contrasts(base,candidate,[2000])
        self.assertEqual(got['features']['precip_mm']['mean'],10.)
        self.assertEqual(got['shape_cells'],1)
        candidate[ZERO]=.25
        got=contrasts(base,candidate,[2000])
        self.assertIsNone(got['features']['stage1_precip_share'])
        self.assertEqual(got['features']['precip_mm']['mean'],10.)
        for bad in (candidate.assign(lat=39.75),pd.concat([candidate,candidate])):
            with self.assertRaises(ValueError):contrasts(base,bad,[2000])
        with self.assertRaises(ValueError):contrasts(base,candidate,[2000,2001])

    def test_season_stage_join(self):
        panel,_=fixture()
        season=panel[[c for c in panel if not c.startswith('stage')]].drop(
            columns=['yield_t_ha','yield_observed'])
        stage_rows=[]
        for _,r in panel.iterrows():
            for i in (1,2,3):
                row={k:r[k] for k in ['harvest_year','lat','lon_360','crop','irrigation']}
                row.update({k[len(f'stage{i}_'):]:r[k] for k in panel if k.startswith(f'stage{i}_')})
                row.update(stage_id=i,stage_fractions='0,0.3,0.7,1')
                stage_rows.append(row)
        joined=join_season_stages(season,pd.DataFrame(stage_rows))
        self.assertTrue(joined.yield_t_ha.isna().all())
        for c in panel:
            np.testing.assert_array_equal(joined[c],panel[c])


if __name__=='__main__':unittest.main()

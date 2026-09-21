import unittest

from compare_five_esm_maize_area_weather import ESMS, summarize
from compare_three_esm_maize_area_weather import FEATURES, SCENARIOS, YEARS


class FiveEsmAreaWeatherTests(unittest.TestCase):
    def test_contrasts_and_stage_reconciliation(self):
        records = []
        for esm in ESMS:
            for scenario in SCENARIOS:
                for year in YEARS:
                    value = {"ssp126": 1.0, "ssp370": 2.0, "ssp585": 4.0}[scenario]
                    fields = {feature: value for feature in FEATURES}
                    fields["precip_mm"] = 3 * value
                    records.append({"esm": esm, "scenario": scenario, "year": year,
                                    "tile_ledgers": [{"area_numerators": fields,
                                                       "equal_sums": fields}]})
        result = summarize(records, 1, 1.0)
        self.assertEqual(result["gfdl-esm4"]["ssp370"]["precip_mm"]["area_weighted"], 3.0)
        self.assertEqual(result["mri-esm2-0"]["ssp585"]["stage2_precip_mm"]["equal_matched_cell"], 3.0)

    def test_missing_year_fails(self):
        records = []
        for esm in ESMS:
            for scenario in SCENARIOS:
                for year in YEARS:
                    if (esm, scenario, year) == (ESMS[-1], "ssp585", YEARS[-1]):
                        continue
                    fields = {feature: 1.0 for feature in FEATURES}
                    fields["precip_mm"] = 3.0
                    records.append({"esm": esm, "scenario": scenario, "year": year,
                                    "tile_ledgers": [{"area_numerators": fields,
                                                       "equal_sums": fields}]})
        with self.assertRaises(ValueError):
            summarize(records, 1, 1.0)


if __name__ == "__main__":
    unittest.main()

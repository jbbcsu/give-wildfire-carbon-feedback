import unittest

from compare_three_esm_maize_area_weather import ESMS, FEATURES, SCENARIOS, YEARS, summarize


class AreaWeatherTests(unittest.TestCase):
    def test_contrast_and_stage_reconciliation(self):
        records = []
        for esm in ESMS:
            for scenario in SCENARIOS:
                for year in YEARS:
                    multiplier = {"ssp126": 1, "ssp370": 2, "ssp585": 3}[scenario]
                    base = {feature: float(multiplier) for feature in FEATURES}
                    base["precip_mm"] = 3*multiplier
                    records.append({"esm": esm, "scenario": scenario, "year": year,
                                    "tile_ledgers": [{"area_numerators": base,
                                                     "equal_sums": base}]})
        result = summarize(records, matched_count=1, matched_area=1)
        self.assertEqual(result["ukesm1-0-ll"]["ssp370"]["precip_mm"]["area_weighted"], 3)
        self.assertEqual(result["mpi-esm1-2-hr"]["ssp585"]["stage1_precip_mm"]["equal_matched_cell"], 2)

    def test_missing_year_rejected(self):
        records = []
        for esm in ESMS:
            for scenario in SCENARIOS:
                for year in YEARS:
                    if esm == ESMS[0] and scenario == "ssp585" and year == YEARS[-1]:
                        continue
                    base = {feature: 1.0 for feature in FEATURES}
                    base["precip_mm"] = 3
                    records.append({"esm": esm, "scenario": scenario, "year": year,
                                    "tile_ledgers": [{"area_numerators": base, "equal_sums": base}]})
        with self.assertRaises(ValueError):
            summarize(records, matched_count=1, matched_area=1)


if __name__ == "__main__":
    unittest.main()

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "data/provenance/five_esm_maize_area_weather_20260921.json"


class FiveEsmPublicClaimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = json.loads(PUBLIC.read_text())
        cls.contrasts = cls.saved["scenario_minus_ssp126"]
        cls.esms = cls.saved["esms"]

    def values(self, scenario, feature):
        return [self.contrasts[esm][scenario][feature]["area_weighted"]
                for esm in self.esms]

    def test_reported_sign_patterns(self):
        cases = {
            ("ssp370", "precip_mm"): (2, 3),
            ("ssp370", "wet_days_n"): (0, 5),
            ("ssp370", "cdd_max_days"): (5, 0),
            ("ssp370", "rx1day_mm"): (4, 1),
            ("ssp370", "rx5day_mm"): (3, 2),
            ("ssp585", "precip_mm"): (3, 2),
            ("ssp585", "wet_days_n"): (0, 5),
            ("ssp585", "cdd_max_days"): (5, 0),
            ("ssp585", "rx1day_mm"): (5, 0),
            ("ssp585", "rx5day_mm"): (4, 1),
        }
        for (scenario, feature), expected in cases.items():
            values = self.values(scenario, feature)
            self.assertEqual((sum(x > 0 for x in values), sum(x < 0 for x in values)), expected)

    def test_main_manuscript_binds_exact_ssp585_rainfall_sequence(self):
        values = self.values("ssp585", "precip_mm")
        expected = "/".join(f"{value:+.2f}" for value in values)
        manuscript = (ROOT / "manuscript/MAIN_MANUSCRIPT.md").read_text()
        self.assertIn(expected, manuscript)

    def test_public_receipt_excludes_annual_ledgers_and_scc(self):
        self.assertNotIn("annual_panels", self.saved)
        self.assertFalse(self.saved["annual_panels_in_public_receipt"])
        self.assertFalse(self.saved["yield_damage_scc_estimated"])
        self.assertEqual(self.saved["audit"]["bound_annual_source_manifests"], 120)


if __name__ == "__main__":
    unittest.main()

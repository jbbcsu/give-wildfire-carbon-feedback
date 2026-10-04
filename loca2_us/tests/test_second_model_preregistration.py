import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[2]


class SecondModelPreregistrationTests(unittest.TestCase):
    def test_ipsl_sentinel_changes_only_model_identity_and_outputs(self):
        gfdl = tomllib.loads((ROOT / "loca2_us/config/loca2_us_cuming_historical_climate_v1.toml").read_text())
        ipsl = tomllib.loads((ROOT / "loca2_us/config/loca2_us_cuming_ipsl_historical_climate_v1.toml").read_text())
        self.assertEqual(ipsl["source"]["source_id"], "IPSL-CM6A-LR")
        self.assertEqual(ipsl["source"]["variant_label"], "r1i1p1f1")
        for key in ("store", "endpoint_url", "precipitation_version", "experiment_id", "variables"):
            self.assertEqual(ipsl["source"][key], gfdl["source"][key])
        for key in (
            "county_geoid", "crop", "year_min", "year_max", "season_start_month_day",
            "season_end_month_day", "wet_day_threshold_mm", "stage_fractions",
            "outcome_columns_read", "paired_year_scoring",
        ):
            self.assertEqual(ipsl["sample"][key], gfdl["sample"][key])
        self.assertEqual(ipsl["inputs"], gfdl["inputs"])
        self.assertEqual(ipsl["resources"], gfdl["resources"])
        self.assertNotEqual(ipsl["outputs"], gfdl["outputs"])
        self.assertFalse(ipsl["sample"]["outcome_columns_read"])
        self.assertTrue(all(value is False for value in ipsl["claim_gates"].values()))


if __name__ == "__main__":
    unittest.main()

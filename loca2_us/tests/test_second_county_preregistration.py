import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[2]


class SecondCountyPreregistrationTests(unittest.TestCase):
    def test_box_butte_changes_county_only(self):
        first = tomllib.loads((ROOT / "loca2_us/config/loca2_us_cuming_historical_climate_v1.toml").read_text())
        second = tomllib.loads((ROOT / "loca2_us/config/loca2_us_box_butte_gfdl_historical_climate_v1.toml").read_text())
        self.assertEqual(second["sample"]["county_geoid"], "31013")
        self.assertIn("farthest", tomllib.loads(
            (ROOT / "loca2_us/config/loca2_us_box_butte_weights_v1.toml").read_text()
        )["county"]["selection_rule"])
        for key in ("store", "endpoint_url", "precipitation_version", "source_id", "experiment_id", "variant_label", "variables"):
            self.assertEqual(second["source"][key], first["source"][key])
        for key in (
            "crop", "year_min", "year_max", "season_start_month_day", "season_end_month_day",
            "wet_day_threshold_mm", "stage_fractions", "outcome_columns_read", "paired_year_scoring",
        ):
            self.assertEqual(second["sample"][key], first["sample"][key])
        self.assertEqual(second["inputs"]["nclimgrid_feature_pattern"], first["inputs"]["nclimgrid_feature_pattern"])
        self.assertFalse(second["sample"]["outcome_columns_read"])
        self.assertTrue(all(value is False for value in second["claim_gates"].values()))


if __name__ == "__main__":
    unittest.main()

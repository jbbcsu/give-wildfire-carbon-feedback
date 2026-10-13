import importlib.util
import math
import json
import sys
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[2]
MODULE_PATH = ROOT / "loca2_us/scripts/preregister_third_county.py"
SPEC = importlib.util.spec_from_file_location("third_county", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

COMBINATION_VALIDATOR_PATH = ROOT / "loca2_us/scripts/validate_historical_climate_partition_combination.py"
sys.path.insert(0, str(COMBINATION_VALIDATOR_PATH.parent))
COMBINATION_SPEC = importlib.util.spec_from_file_location("combination_validator", COMBINATION_VALIDATOR_PATH)
COMBINATION_VALIDATOR = importlib.util.module_from_spec(COMBINATION_SPEC)
assert COMBINATION_SPEC.loader is not None
COMBINATION_SPEC.loader.exec_module(COMBINATION_VALIDATOR)


class ThirdCountyPreregistrationTests(unittest.TestCase):
    def test_haversine_identity_and_symmetry(self):
        a = (41.0, -96.0)
        b = (42.0, -103.0)
        self.assertEqual(MODULE.haversine_km(a, a), 0.0)
        self.assertAlmostEqual(MODULE.haversine_km(a, b), MODULE.haversine_km(b, a), places=12)

    def test_no_outcome_columns_in_contract(self):
        self.assertNotIn("yield_bu_acre", MODULE.READ_COLUMNS)
        self.assertNotIn("source_value_raw", MODULE.READ_COLUMNS)
        self.assertEqual(MODULE.ANCHORS, ("31039", "31013"))
        self.assertEqual(set(MODULE.YEARS), set(range(2001, 2013)))

    def test_furnas_weight_config_matches_preregistration(self):
        selection = json.loads((ROOT / "loca2_us/data/provenance/loca2_third_county_preregistration_20261013.json").read_text())
        config = tomllib.loads((ROOT / "loca2_us/config/loca2_us_furnas_weights_v1.toml").read_text())
        self.assertEqual(selection["selected"]["county_geoid"], "31065")
        self.assertEqual(config["county"]["geoid"], selection["selected"]["county_geoid"])
        self.assertIn("maximize the minimum", config["county"]["selection_rule"])
        self.assertTrue(all(value is False for value in config["claim_gates"].values()))

    def test_direct_chunk_matrix_is_frozen_and_nonoverlapping(self):
        configs = {}
        for model in ("gfdl", "ipsl"):
            for span in ("2001_2006", "2007_2012"):
                path = ROOT / f"loca2_us/config/loca2_us_furnas_{model}_historical_{span}_direct_v2.toml"
                configs[(model, span)] = tomllib.loads(path.read_text())
        self.assertEqual({item["source"]["source_id"] for item in configs.values()}, {"GFDL-ESM4", "IPSL-CM6A-LR"})
        for item in configs.values():
            self.assertEqual(item["sample"]["county_geoid"], "31065")
            self.assertFalse(item["sample"]["outcome_columns_read"])
            self.assertFalse(item["sample"]["paired_year_scoring"])
            self.assertEqual(item["resources"]["spatial_accumulator"], "one_source_spatial_chunk_variable_serial_v2")
            self.assertTrue(all(value is False for value in item["claim_gates"].values()))
        for model in ("gfdl", "ipsl"):
            first, second = configs[(model, "2001_2006")], configs[(model, "2007_2012")]
            self.assertEqual(first["sample"]["year_max"] + 1, second["sample"]["year_min"])
            self.assertEqual(first["source"], second["source"])

    def test_combined_furnas_artifacts_revalidate_independently(self):
        for model in ("gfdl", "ipsl"):
            path = ROOT / f"loca2_us/data/provenance/loca2_furnas_{model}_historical_climate_sentinel_2001_2012_direct_v2_20261013.json"
            result = COMBINATION_VALIDATOR.validate(json.loads(path.read_text()))
            self.assertEqual(result["maximum_absolute_saved_precision_difference"], 0.0)
            self.assertGreater(result["checks"], 500)


if __name__ == "__main__":
    unittest.main()

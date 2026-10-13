import hashlib
import importlib.util
import json
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "loca2_us/scripts/preregister_compact_strata_expansion.py"
SPEC = importlib.util.spec_from_file_location("compact_strata", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
CONFIG_PATH = ROOT / "loca2_us/config/loca2_us_compact_strata_expansion_v1.toml"
RECEIPT_PATH = ROOT / "loca2_us/data/provenance/loca2_compact_strata_expansion_preregistration_20261013.json"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


class CompactStrataExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = tomllib.loads(CONFIG_PATH.read_text())
        cls.receipt = json.loads(RECEIPT_PATH.read_text())

    def test_input_contract_excludes_outcomes_and_climate_values(self):
        read_columns = set(MODULE.PANEL_COLUMNS) | set(MODULE.CALENDAR_COLUMNS)
        self.assertFalse(read_columns & MODULE.FORBIDDEN_COLUMNS)
        contract = self.receipt["input_access_contract"]
        self.assertFalse(contract["yield_magnitudes_read"])
        self.assertFalse(contract["nclimgrid_climate_values_read"])
        self.assertFalse(contract["loca2_climate_values_read"])

    def test_state_groups_and_selection_order_are_frozen(self):
        order = self.config["selection"]["stratum_order"]
        self.assertEqual(order, ["western_irrigated", "southeast_early_rainfed", "humid_midwest_late_rainfed"])
        state_sets = [set(self.config["strata"][name]["states"]) for name in order]
        self.assertFalse(state_sets[0] & state_sets[1])
        self.assertFalse(state_sets[0] & state_sets[2])
        self.assertFalse(state_sets[1] & state_sets[2])
        self.assertEqual(self.config["selection"]["exclude_states"], ["NE"])

    def test_selection_is_reproducible_from_metadata_only(self):
        candidates, audit = MODULE.build_candidates(self.config)
        selected, counts = MODULE.select_counties(candidates, self.config, audit["points"])
        self.assertEqual([row["county_geoid"] for row in selected], ["06095", "13131", "18145"])
        self.assertEqual([row["county_geoid"] for row in selected], [row["county_geoid"] for row in self.receipt["selected"]])
        self.assertEqual(counts, self.receipt["support"]["stratum_candidate_counts"])

    def test_selected_weight_readiness_is_hash_bound(self):
        for geoid, item in self.receipt["selected_nclimgrid_weight_readiness"].items():
            self.assertIn(geoid, {"06095", "13131", "18145"})
            self.assertEqual(digest(ROOT / item["receipt_path"]), item["receipt_sha256"])
            self.assertEqual(digest(ROOT / item["output_path"]), item["output_sha256"])
            self.assertGreater(item["positive_weather_cells"], 0)
            self.assertGreaterEqual(item["coverage_fraction"], 0.999)
            self.assertGreaterEqual(item["weather_valid_area_relative_to_declared_land"], 0.95)

    def test_execution_plan_is_serial_deferred_and_complete(self):
        plan = self.receipt["execution_plan"]
        self.assertFalse(plan["downloads_launched"])
        self.assertEqual(plan["planned_climate_job_count"], 12)
        jobs = plan["planned_climate_jobs"]
        matrix = {(job["county_geoid"], job["source_id"], job["year_min"], job["year_max"]) for job in jobs}
        self.assertEqual(len(matrix), 12)
        self.assertEqual({job["county_geoid"] for job in jobs}, {"06095", "13131", "18145"})
        self.assertEqual({job["source_id"] for job in jobs}, {"GFDL-ESM4", "IPSL-CM6A-LR"})
        self.assertEqual({(job["year_min"], job["year_max"]) for job in jobs}, {(2001, 2006), (2007, 2012)})
        self.assertTrue(all(job["status"].startswith("blocked_until_") for job in jobs))
        resources = plan["resources"]
        self.assertEqual(resources["worker_memory_mib"], 512)
        self.assertTrue(resources["county_serial"] and resources["model_serial"] and resources["partition_serial"])

    def test_claim_gates_are_fail_closed(self):
        gates = self.receipt["claim_gates"]
        self.assertTrue(gates["compact_county_design_selected"])
        self.assertTrue(all(value is False for key, value in gates.items() if key != "compact_county_design_selected"))


if __name__ == "__main__":
    unittest.main()

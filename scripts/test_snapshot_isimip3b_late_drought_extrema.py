import unittest

from snapshot_isimip3b_late_drought_extrema import (
    ESMS, MEMBERS, SCENARIOS, VARIABLES, build_snapshot,
)


class LateDroughtSnapshotTests(unittest.TestCase):
    def rows(self):
        return [
            {"forcing": esm, "member": MEMBERS[esm], "scenario": scenario,
             "variable": variable, "dataset_id": f"{esm}-{scenario}-{variable}"}
            for esm in ESMS for scenario in SCENARIOS for variable in VARIABLES
        ]

    def dataset(self, dataset_url):
        dataset_id = dataset_url.rstrip("/").split("/")[-1]
        esm, scenario, variable = next(
            (esm, scenario, variable) for esm in ESMS for scenario in SCENARIOS for variable in VARIABLES
            if dataset_id == f"{esm}-{scenario}-{variable}"
        )
        name = f"{esm}_{MEMBERS[esm]}_w5e5_{scenario}_{variable}_global_daily_2091_2100.nc"
        return {
            "id": dataset_id, "version": "20210512", "public": True, "restricted": False,
            "rights": {"short": "CC0 1.0"}, "url": f"https://example/{dataset_id}",
            "specifiers": {
                "region": "global", "product": "InputData", "category": "climate",
                "time_step": "daily", "subcategory": "atmosphere", "bias_adjustment": "w5e5",
                "climate_forcing": esm, "ensemble_member": MEMBERS[esm],
                "climate_scenario": scenario, "climate_variable": variable,
                "simulation_round": "ISIMIP3b",
            },
            "files": [{"id": "file", "name": name, "version": "20210512", "size": 10,
                       "checksum": "a" * 128, "checksum_type": "sha512",
                       "file_url": f"https://files.isimip.org/{name}"}],
            "resources": [{"doi": "10.48364/ISIMIP.842396.1"}],
        }

    def test_exact_matrix(self):
        output = build_snapshot(self.rows(), self.dataset)
        self.assertEqual(output["object_count"], 30)
        self.assertEqual(output["total_bytes"], 300)
        self.assertFalse(output["raw_objects_downloaded_by_snapshot"])

    def test_missing_row_fails(self):
        with self.assertRaises(ValueError):
            build_snapshot(self.rows()[:-1], self.dataset)

    def test_changed_rights_fail(self):
        def changed(dataset_id):
            value = self.dataset(dataset_id)
            value["rights"]["short"] = "NOASSERTION"
            return value
        with self.assertRaises(ValueError):
            build_snapshot(self.rows(), changed)


if __name__ == "__main__":
    unittest.main()

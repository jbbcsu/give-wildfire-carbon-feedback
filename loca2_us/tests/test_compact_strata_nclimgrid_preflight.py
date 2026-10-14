import csv
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "loca2_us/scripts/preflight_compact_strata_nclimgrid_features.py"
SPEC = importlib.util.spec_from_file_location("compact_nclimgrid_preflight", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
RECEIPT = ROOT / "loca2_us/data/provenance/loca2_compact_strata_nclimgrid_local_availability_20261014.json"


class CompactStrataNclimgridPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = json.loads(RECEIPT.read_text())

    def test_exact_month_union_is_calendar_derived(self):
        prereg = json.loads(MODULE.DEFAULT_PREREGISTRATION.read_text())
        keys, by_county = MODULE.derive_required_keys(prereg)
        self.assertEqual(len(keys), 84)
        self.assertEqual(keys, [(year, month) for year in range(2001, 2013) for month in range(4, 11)])
        self.assertEqual(len(by_county["06095"]), 72)
        self.assertEqual(len(by_county["13131"]), 72)
        self.assertEqual(len(by_county["18145"]), 72)

    def test_exact_manifest_and_local_blocker(self):
        receipt = self.receipt
        self.assertEqual(receipt["required_object_count"], 84)
        self.assertEqual(receipt["required_bytes"], 4_909_747_416)
        self.assertAlmostEqual(receipt["required_gib"], 4.572558604180813)
        self.assertEqual(receipt["status"], "blocked_missing_resident_gridded_weather")
        self.assertEqual(receipt["local_availability"]["valid_object_count"], 0)
        self.assertEqual(receipt["local_availability"]["missing_object_count"], 84)
        self.assertEqual(receipt["local_availability"]["partial_object_count"], 0)
        self.assertEqual(receipt["local_availability"]["invalid_object_count"], 0)
        self.assertEqual(
            MODULE.canonical_sha256(receipt["required_objects"]),
            receipt["required_object_manifest_sha256"],
        )

    def test_manifest_is_exact_source_intersection(self):
        with MODULE.DEFAULT_INVENTORY.open(newline="") as stream:
            inventory = {row["name"]: row for row in csv.DictReader(stream)}
        content = json.loads(MODULE.DEFAULT_CONTENT_RECEIPT.read_text())
        content_by_name = {row["name"]: row for row in content["objects"]}
        required = self.receipt["required_objects"]
        self.assertEqual(len({row["name"] for row in required}), 84)
        self.assertEqual(sum(int(inventory[row["name"]]["content_length"]) for row in required), 4_909_747_416)
        for row in required:
            source = inventory[row["name"]]
            hashed = content_by_name[row["name"]]
            self.assertEqual(row["canonical_url"], source["canonical_url"])
            self.assertEqual(row["content_length"], int(source["content_length"]))
            self.assertEqual(row["expected_local_sha512"], hashed["local_sha512"])
        self.assertEqual(
            {row["period"] for row in self.receipt["local_availability"]["missing"]},
            {row["period"] for row in required},
        )

    def test_local_classifier_fails_closed(self):
        payload = b"local-test-object"
        item = {
            "period": "2001-04", "name": "example.nc", "content_length": len(payload),
            "expected_local_sha512": hashlib.sha512(payload).hexdigest(),
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid, missing, partial, invalid = MODULE.classify_local_objects([item], root)
            self.assertEqual(len(missing), 1)
            (root / "example.nc.part").write_bytes(payload)
            valid, missing, partial, invalid = MODULE.classify_local_objects([item], root)
            self.assertEqual(len(partial), 1)
            (root / "example.nc.part").unlink()
            (root / "example.nc").write_bytes(b"wrong")
            valid, missing, partial, invalid = MODULE.classify_local_objects([item], root)
            self.assertEqual(len(invalid), 1)
            self.assertEqual(invalid[0]["reason"], "size")
            (root / "example.nc").write_bytes(b"x" * len(payload))
            valid, missing, partial, invalid = MODULE.classify_local_objects([item], root)
            self.assertEqual(len(invalid), 1)
            self.assertEqual(invalid[0]["reason"], "sha512")
            (root / "example.nc").write_bytes(payload)
            valid, missing, partial, invalid = MODULE.classify_local_objects([item], root)
            self.assertEqual(len(valid), 1)
            self.assertFalse(missing or partial or invalid)

    def test_no_network_or_county_average_substitution(self):
        source = SCRIPT.read_text()
        for forbidden in ("requests.", "urlopen(", "subprocess.", "curl ", "wget "):
            self.assertNotIn(forbidden, source)
        self.assertFalse(self.receipt["network_operations_performed"])
        self.assertFalse(self.receipt["raw_data_written_or_modified"])
        self.assertFalse(self.receipt["reacquisition_authorized"])
        self.assertFalse(self.receipt["substitution_gate"]["resident_noaa_county_average_csvs_authorized"])
        self.assertFalse(self.receipt["feature_build_gate"]["existing_all_practice_builder_authorized_for_this_task"])

    def test_weight_and_source_bindings_are_current(self):
        for item in self.receipt["selected_weight_bindings"].values():
            self.assertEqual(MODULE.sha256(ROOT / item["receipt_path"]), item["receipt_sha256"])
            self.assertEqual(MODULE.sha256(ROOT / item["output_path"]), item["output_sha256"])
        for item in self.receipt["source_bindings"].values():
            self.assertEqual(MODULE.sha256(ROOT / item["path"]), item["sha256"])

    def test_claim_gates_remain_closed_beyond_availability_audit(self):
        gates = self.receipt["claim_gates"]
        self.assertTrue(gates["local_input_availability_audited"])
        self.assertTrue(all(value is False for key, value in gates.items() if key != "local_input_availability_audited"))


if __name__ == "__main__":
    unittest.main()

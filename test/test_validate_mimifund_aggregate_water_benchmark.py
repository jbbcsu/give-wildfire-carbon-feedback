import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from validate_mimifund_aggregate_water_benchmark import validate  # noqa: E402

CONFIG = ROOT / "config/mimifund_aggregate_water_benchmark_v1.json"


class AggregateWaterBenchmarkTests(unittest.TestCase):
    def test_checked_in_benchmark_validates(self):
        result = validate(CONFIG)
        self.assertEqual(result["status"], "passed_external_aggregate_water_benchmark_not_municipal")
        self.assertFalse(result["additive_to_baseline_give"])

    def test_open_additivity_gate_fails(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        config["hard_gates"]["additive_to_baseline_give"] = True
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "scientific gate"):
                validate(path)

    def test_output_hash_tampering_fails(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        config["outputs"]["cases"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "output mismatch"):
                validate(path)

    def test_false_municipal_label_cannot_pass(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        config["hard_gates"]["municipal_endpoint_isolated"] = True
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "scientific gate"):
                validate(path)

    def test_drought_response_cannot_be_invented(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        config["hard_gates"]["drought_or_hydrology_response_explicit"] = True
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "scientific gate"):
                validate(path)


if __name__ == "__main__":
    unittest.main()

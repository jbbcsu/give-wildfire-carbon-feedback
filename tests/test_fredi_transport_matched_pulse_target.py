import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_fredi_transport_matched_pulse_target as target
import validate_give_transport_temperature_pair as pair_validation


CONFIG = ROOT / "config/fredi_transport_matched_pulse_v1.json"


class TransportMatchedPulseTargetTests(unittest.TestCase):
    def test_official_runtime_target_is_ready(self):
        result = target.audit(ROOT, CONFIG)
        self.assertEqual(result["status"], "target_ready_climate_pair_and_scc_gates_closed")
        self.assertEqual(result["verified"]["state_dc_count"], 49)
        self.assertEqual(result["verified"]["gcm_count"], 6)
        self.assertEqual(result["verified"]["primary_reactive_aggregates"], ["Roads", "Rail"])
        self.assertTrue(result["verified"]["runtime_through_2300"])
        self.assertFalse(result["claim_gates"]["conus_partial_scc_authorized"])

    def test_matched_give_temperature_pair_passes(self):
        result = pair_validation.validate(ROOT, CONFIG)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["rows"], 551)
        self.assertTrue(result["pre_pulse_identity"])
        self.assertTrue(result["official_conus_conversion_recomputed"])
        self.assertGreater(result["max_pulse_gmst_difference_c"], 0)

    def test_global_claim_fails_closed(self):
        config = json.loads(CONFIG.read_text())
        config["selection"]["global_scc_claim_allowed"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.json"
            path.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, "global claim"):
                target.audit(ROOT, path)

    def test_premature_scc_gate_fails_closed(self):
        config = json.loads(CONFIG.read_text())
        config["claim_gates"]["conus_partial_scc_authorized"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.json"
            path.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, "prematurely open"):
                target.audit(ROOT, path)

    def test_unofficial_temperature_conversion_fails_closed(self):
        config = json.loads(CONFIG.read_text())
        config["response"]["global_to_conus_multiplier"] = 1.4
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.json"
            path.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, "conversion differs"):
                target.audit(ROOT, path)

    def test_component_unbundling_is_not_invented(self):
        config = json.loads(CONFIG.read_text())
        self.assertEqual(set(config["response"]["component_semantics"]), {"Roads", "Rail"})
        self.assertIn("inseparable", config["response"]["component_semantics"]["Roads"])
        self.assertIn("inseparable", config["response"]["component_semantics"]["Rail"])


if __name__ == "__main__":
    unittest.main()

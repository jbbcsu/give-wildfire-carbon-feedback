import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "python"))

from validate_replication_request import audit_official_repository, sha256, validate_request  # noqa: E402


def request() -> dict[str, object]:
    return json.loads((ROOT / "config/biodiversity_replication_request_v1.json").read_text(encoding="utf-8"))


class ReplicationRequestTests(unittest.TestCase):
    def test_current_request_is_valid_but_blocked(self):
        result = validate_request(request())
        self.assertTrue(result["request_contract_valid"])
        self.assertEqual(result["artifact_group_count"], 7)
        self.assertFalse(result["damage_or_scc_authorized"])

    def test_authorization_fails_closed(self):
        candidate = request()
        candidate["target_component"]["authorized_for_give"] = True
        with self.assertRaisesRegex(ValueError, "GIVE must remain unauthorized"):
            validate_request(candidate)

    def test_benchmark_as_calibration_fails(self):
        candidate = request()
        candidate["target_component"]["published_benchmark_is_calibration"] = True
        with self.assertRaisesRegex(ValueError, "benchmark cannot be calibration"):
            validate_request(candidate)

    def test_missing_artifact_group_fails(self):
        candidate = request()
        candidate["required_artifacts"].pop()
        with self.assertRaisesRegex(ValueError, "seven artifact groups"):
            validate_request(candidate)

    def test_missing_license_gate_fails(self):
        candidate = request()
        candidate["required_artifacts"][0]["license_required"] = False
        with self.assertRaisesRegex(ValueError, "license is not required"):
            validate_request(candidate)

    def test_missing_overlap_exclusion_fails(self):
        candidate = request()
        candidate["overlap_boundary"]["excluded"].remove("fisheries_and_aquaculture")
        with self.assertRaisesRegex(ValueError, "overlap exclusions"):
            validate_request(candidate)

    def test_claimed_receipt_requires_separate_audit(self):
        candidate = copy.deepcopy(request())
        candidate["current_gate"]["received_artifact_groups"] = ["A1_executable_source_environment"]
        with self.assertRaisesRegex(ValueError, "separate receipt audit"):
            validate_request(candidate)

    def test_pinned_source_without_terms_passes(self):
        candidate = request()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.txt"
            source.write_text("ordinary model source\n", encoding="utf-8")
            audit = candidate["official_repository_audit"]
            audit["commit"] = "a" * 40
            audit["tracked_file_count"] = 1
            audit["pinned_files"] = {"source.txt": sha256(source)}
            with mock.patch(
                "validate_replication_request.git_output",
                side_effect=["a" * 40, "source.txt"],
            ):
                result = audit_official_repository(candidate, root)
        self.assertFalse(result["biodiversity_component_found"])

    def test_new_source_term_forces_reaudit(self):
        candidate = request()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.txt"
            source.write_text("new biodiversity module\n", encoding="utf-8")
            audit = candidate["official_repository_audit"]
            audit["commit"] = "a" * 40
            audit["tracked_file_count"] = 1
            audit["pinned_files"] = {"source.txt": sha256(source)}
            with mock.patch(
                "validate_replication_request.git_output",
                side_effect=["a" * 40, "source.txt"],
            ):
                with self.assertRaisesRegex(ValueError, "search result changed"):
                    audit_official_repository(candidate, root)


if __name__ == "__main__":
    unittest.main()

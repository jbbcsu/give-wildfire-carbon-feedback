from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from fredi_transport_heat_common import (  # noqa: E402
    ContractError,
    compute_smoke,
    linear_interpolate,
    read_json,
    validate_contract,
)


def config():
    return read_json(ROOT / "config/fredi_transport_heat_v4_1_1.json")


class TransportHeatSmokeTests(unittest.TestCase):
    def test_piecewise_linear_sentinel_and_no_extrapolation(self):
        self.assertEqual(
            linear_interpolate(Decimal("-2"), Decimal("6"), Decimal("1.5")),
            Decimal("2.0"),
        )
        with self.assertRaisesRegex(ContractError, "restricted"):
            linear_interpolate(Decimal("0"), Decimal("1"), Decimal("2.1"))

    def test_component_gates_are_fail_closed_before_source_access(self):
        altered = deepcopy(config())
        altered["component_gates"][0]["available_in_public_v4_1_1_runtime"] = True
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ContractError, "four component endpoints"):
                validate_contract(Path(directory), altered)

    def test_manifest_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            source = temporary / "tampered.csv"
            source.write_text("tampered\n", encoding="utf-8")
            manifest = {
                "files": [{
                    "path": "x",
                    "raw_path": str(source),
                    "bytes": source.stat().st_size,
                    "sha256": "0" * 64,
                }]
            }
            (temporary / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            altered = deepcopy(config())
            altered["source_manifest"] = "manifest.json"
            altered["alignment_audit"] = str(
                ROOT / "provenance/fredi_v4_1_1_transport_alignment_audit.json"
            )
            with self.assertRaisesRegex(ContractError, "SHA-256 mismatch"):
                validate_contract(temporary, altered)

    def test_embedded_version_alignment_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            bad_alignment = {
                "status": "PASS",
                "tolerance": 1e-12,
                "comparisons": [{"max_abs_difference": 1e-6}],
            }
            (temporary / "alignment.json").write_text(
                json.dumps(bad_alignment), encoding="utf-8"
            )
            altered = deepcopy(config())
            altered["source_manifest"] = str(
                ROOT / "provenance/fredi_source_manifest_v4_1_1.json"
            )
            altered["alignment_audit"] = "alignment.json"
            with self.assertRaisesRegex(ContractError, "alignment exceeds tolerance"):
                validate_contract(temporary, altered)

    def test_official_bounded_surface_and_output_schema(self):
        rows, diagnostics = compute_smoke(ROOT, config())
        self.assertEqual(diagnostics, {
            "state_dc_count": 49,
            "gcm_count": 6,
            "variant_count": 3,
            "released_aggregate_count": 2,
            "output_row_count": 36,
        })
        self.assertEqual({row["released_aggregate"] for row in rows}, {"Roads", "Rail"})
        self.assertEqual(
            {row["component_resolution"] for row in rows},
            {"combined_public_surface"},
        )
        self.assertFalse(any("endpoint" in row for row in rows))
        self.assertFalse(any("scc" in key.lower() for key in rows[0]))

    def test_scripts_pass_without_network_or_forbidden_sources(self):
        verify = subprocess.run(
            [sys.executable, str(ROOT / "scripts/acquire_pinned_fredi_sources.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('"downloaded_files": 0', verify.stdout)
        validate = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate_fredi_transport_heat_smoke.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('"status": "PASS"', validate.stdout)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import subprocess
import sys
import unittest
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from fredi_electricity_heat_common import (  # noqa: E402
    ElectricityContractError,
    compute_sentinel,
    interpolate,
    read_json,
    validate_contract,
)


def config():
    return read_json(ROOT / "config/fredi_electricity_heat_v4_1_1.json")


class ElectricityTDSentinelTests(unittest.TestCase):
    def test_linear_sentinel_and_extrapolation_rejection(self):
        self.assertEqual(interpolate(Decimal("4"), Decimal("10"), Decimal("1.5")), Decimal("7.0"))
        with self.assertRaisesRegex(ElectricityContractError, "restricted"):
            interpolate(Decimal("4"), Decimal("10"), Decimal("0.9"))

    def test_generation_capacity_bundle_cannot_be_opened(self):
        altered = deepcopy(config())
        for gate in altered["endpoint_gates"]:
            if gate["endpoint"] == "generation_and_capacity":
                gate["authorized_for_output"] = True
        with self.assertRaisesRegex(ElectricityContractError, "forbidden endpoint"):
            validate_contract(ROOT, altered)

    def test_bundled_electricity_demand_supply_sector_cannot_be_computed(self):
        altered = deepcopy(config())
        altered["scope"]["authorized_released_sector"] = "ElecSD"
        with self.assertRaisesRegex(ElectricityContractError, "only released ElecTD"):
            validate_contract(ROOT, altered)

    def test_official_surface_computes_td_only(self):
        records, diagnostics = compute_sentinel(ROOT, config())
        self.assertEqual(diagnostics, {
            "state_dc_count": 49,
            "gcm_count": 6,
            "variant_count": 3,
            "output_row_count": 18,
            "computed_sectors": ["ElecTD"],
            "audited_excluded_sectors": ["ElecSD"],
        })
        self.assertEqual({row["released_sector"] for row in records}, {"ElecTD"})
        self.assertEqual(
            {row["endpoint_resolution"] for row in records},
            {"combined_transmission_distribution"},
        )
        self.assertFalse(any("scc" in key.lower() for key in records[0]))

    def test_independent_validator_and_offline_source_verifier(self):
        source_check = subprocess.run(
            [sys.executable, str(ROOT / "scripts/acquire_pinned_fredi_sources.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('"downloaded_files": 0', source_check.stdout)
        validation = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate_fredi_electricity_td_heat_sentinel.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('"status": "PASS"', validation.stdout)


if __name__ == "__main__":
    unittest.main()

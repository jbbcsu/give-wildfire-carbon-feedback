import copy
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parents[1] / "python"))

from biodiversity_kernel import climate_deficit, country_damage  # noqa: E402
from validate_biodiversity_pair import audit_pair  # noqa: E402


def row(year: int, temperature: float, stock: float) -> dict[str, object]:
    no_climate_stock = 0.95
    deficit = climate_deficit(no_climate_stock, stock)
    damage = country_damage(10.0, 100.0, stock, deficit, beta=2.0)
    return {
        "draw_id": "draw-1",
        "climate_realization_id": "climate-1",
        "socioeconomic_draw_id": "socioeconomic-1",
        "valuation_draw_id": "valuation-1",
        "country_id": "AAA",
        "year": year,
        "temperature_change": temperature,
        "population": 10.0,
        "income": 100.0,
        "no_climate_stock": no_climate_stock,
        "climate_stock": stock,
        "deficit": deficit,
        "beta": 2.0,
        "damage": damage,
    }


def bundle(role: str, pulse_size: float, post_stock: float) -> dict[str, object]:
    return {
        "schema": "biodiversity_nonuse_pair_v1",
        "path_role": role,
        "pulse_size_gtc": pulse_size,
        "first_divergence_year": 2021,
        "rows": [row(2020, 1.0, 0.90), row(2021, 1.1 if role == "baseline" else 1.2, post_stock)],
    }


class BiodiversityPairAuditTests(unittest.TestCase):
    def test_matched_pair(self):
        result = audit_pair(bundle("baseline", 0.0, 0.89), bundle("pulse", 1.0, 0.88))
        self.assertTrue(result["pre_divergence_identity"])
        self.assertFalse(result["zero_pulse_identity"])
        self.assertFalse(result["damage_or_scc_authorized"])

    def test_zero_pulse_identity(self):
        baseline = bundle("baseline", 0.0, 0.89)
        pulse = copy.deepcopy(baseline)
        pulse["path_role"] = "pulse"
        result = audit_pair(baseline, pulse)
        self.assertTrue(result["zero_pulse_identity"])

    def test_mismatched_key_fails(self):
        pulse = bundle("pulse", 1.0, 0.88)
        pulse["rows"][1]["country_id"] = "BBB"
        with self.assertRaisesRegex(ValueError, "keys differ"):
            audit_pair(bundle("baseline", 0.0, 0.89), pulse)

    def test_pre_divergence_change_fails(self):
        pulse = bundle("pulse", 1.0, 0.88)
        pulse["rows"][0] = row(2020, 1.0, 0.89)
        with self.assertRaisesRegex(ValueError, "pre-divergence identity"):
            audit_pair(bundle("baseline", 0.0, 0.89), pulse)

    def test_nonreproducing_damage_fails(self):
        pulse = bundle("pulse", 1.0, 0.88)
        pulse["rows"][1]["damage"] += 1.0
        with self.assertRaisesRegex(ValueError, "damage does not reproduce"):
            audit_pair(bundle("baseline", 0.0, 0.89), pulse)

    def test_mismatched_draw_identity_fails(self):
        pulse = bundle("pulse", 1.0, 0.88)
        pulse["rows"][1]["valuation_draw_id"] = "valuation-2"
        with self.assertRaisesRegex(ValueError, "paired fixed field differs"):
            audit_pair(bundle("baseline", 0.0, 0.89), pulse)

    def test_unregistered_bundle_field_fails(self):
        pulse = bundle("pulse", 1.0, 0.88)
        pulse["unregistered"] = True
        with self.assertRaisesRegex(ValueError, "bundle schema changed"):
            audit_pair(bundle("baseline", 0.0, 0.89), pulse)


if __name__ == "__main__":
    unittest.main()

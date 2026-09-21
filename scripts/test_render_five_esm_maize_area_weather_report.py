import unittest

from compare_five_esm_maize_area_weather import ESMS
from compare_three_esm_maize_area_weather import FEATURES, SCENARIOS
from render_five_esm_maize_area_weather_report import LABELS, render, sign_counts


class FiveEsmReportTests(unittest.TestCase):
    def fixture(self):
        contrasts = {}
        for index, esm in enumerate(ESMS):
            contrasts[esm] = {}
            for scenario in SCENARIOS[1:]:
                contrasts[esm][scenario] = {
                    feature: {"area_weighted": float(index - 2)} for feature in FEATURES
                }
        result = {
            "status": "five_esm_fixed_maize_area_weather_only_not_forced_response_or_scc",
            "matched_calendar_cells": 30654,
            "matched_area_fraction": 0.999559,
            "esms": list(ESMS),
            "scenarios": list(SCENARIOS),
            "scenario_minus_ssp126": contrasts,
            "models_are_not_probability_draws": True,
            "yield_damage_scc_estimated": False,
        }
        audit = {
            "status": "independent_five_esm_fixed_area_weather_ledger_and_source_sample_passed",
            "primary_sha256": "primary",
            "annual_numeric_checks": 2160,
            "contrast_numeric_checks": 180,
            "fixed_source_tile_checks": 210,
            "bound_annual_source_manifests": 120,
            "no_yield_damage_scc_estimated": True,
        }
        return result, audit

    def test_render_binds_audit_and_reports_signs(self):
        result, audit = self.fixture()
        text = render(result, audit, "primary", "audit")
        self.assertIn("2 positive / 2 negative / 1 zero", text)
        self.assertIn("all 120 annual source manifests", text)
        self.assertIn("**not** a probability", text)

    def test_wrong_hash_fails(self):
        result, audit = self.fixture()
        with self.assertRaises(ValueError):
            render(result, audit, "different", "audit")

    def test_incomplete_audit_fails(self):
        result, audit = self.fixture()
        audit["bound_annual_source_manifests"] = 119
        with self.assertRaises(ValueError):
            render(result, audit, "primary", "audit")

    def test_sign_counts(self):
        self.assertEqual(sign_counts([-2.0, -1.0, 0.0, 1.0, 2.0]),
                         "2 positive / 2 negative / 1 zero")

    def test_every_feature_has_a_label(self):
        self.assertEqual(set(LABELS), set(FEATURES))


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Fail if reviewed umbrella milestones drift across public claim surfaces."""

import hashlib
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "data" / "provenance" / "sector_status_20261014.json"


class CrossFileClaimConsistencyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.status = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        cls.sectors = {row["name"]: row for row in cls.status["sectors"]}
        cls.registry = (ROOT / "SECTOR_REGISTRY.md").read_text(encoding="utf-8")
        cls.main = (ROOT / "manuscript" / "MAIN_MANUSCRIPT.md").read_text(
            encoding="utf-8"
        )
        cls.methods = (
            ROOT / "manuscript" / "METHODS_SUPPORTING_INFORMATION.md"
        ).read_text(encoding="utf-8")

    def test_all_sector_values_remain_nonadditive(self):
        self.assertEqual(len(self.status["evidence_receipts"]), 8)
        for receipt in self.status["evidence_receipts"]:
            self.assertEqual(len(receipt["sha256"]), 64)
            self.assertGreater(receipt["bytes"], 0)
        self.assertFalse(self.status["external_benchmarks_summed"])
        self.assertFalse(self.status["integrated_increment_calculated"])
        self.assertTrue(self.status["promotion_gates_closed"])
        self.assertTrue(all(row["additive"] is False for row in self.status["sectors"]))

    def test_evidence_receipt_hashes_when_sibling_projects_are_present(self):
        checked = 0
        for receipt in self.status["evidence_receipts"]:
            project = ROOT.parent / receipt["project"]
            if not project.is_dir():
                continue
            source = f'{receipt["source_commit"]}:{receipt["path"]}'
            result = subprocess.run(
                ["git", "-C", str(project), "show", source],
                check=False,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
            self.assertEqual(len(result.stdout), receipt["bytes"], source)
            self.assertEqual(
                hashlib.sha256(result.stdout).hexdigest(), receipt["sha256"], source
            )
            checked += 1
        if checked:
            self.assertEqual(checked, len(self.status["evidence_receipts"]))

    def test_spei_progress_matches_claim_surfaces(self):
        spei = self.sectors["us_rainfed_maize_future_spei_exposure"]
        self.assertEqual(spei["future_extension_cases_validated"], 5)
        self.assertEqual(spei["future_extension_cases_total"], 15)
        self.assertEqual(spei["future_extension_cases_remaining"], 10)
        self.assertFalse(spei["bridge_complete"])
        self.assertIn("5 of 15", self.registry)
        self.assertIn("Five of", self.main)
        self.assertIn("Five of", self.methods)

    def test_moore_preflight_and_memory_bound_match_claim_surfaces(self):
        labor = self.sectors["labor_productivity"]
        self.assertTrue(labor["paired_module_source_graph_verified"])
        self.assertTrue(labor["structural_cases_separate"])
        self.assertFalse(labor["target_give_run_completed"])
        self.assertEqual(labor["legacy_branch_peak_rss_bytes"], 2_531_426_304)
        self.assertGreater(
            labor["legacy_branch_peak_rss_bytes"], labor["worker_memory_limit_bytes"]
        )
        self.assertFalse(labor["replacement_delta_promoted"])
        self.assertFalse(labor["pooled_uncertainty_constructed"])
        for document in (self.registry, self.main, self.methods):
            self.assertIn("2,531,426,304", document)

    def test_fisheries_and_biodiversity_rejections_match_claim_surfaces(self):
        fisheries = self.sectors["fisheries_market_and_nutrition"]
        self.assertEqual(fisheries["comparable_fisheries_summary_rows"], 2)
        self.assertEqual(fisheries["additive_fisheries_summary_rows"], 0)
        self.assertEqual(
            fisheries["annual_pair_public_summary_status"],
            "rejected_not_matched_annual_artifact_package",
        )
        biodiversity = self.sectors["biodiversity_nonuse"]
        self.assertEqual(biodiversity["received_complete_artifact_groups"], 0)
        self.assertEqual(biodiversity["required_artifact_groups"], 7)
        self.assertEqual(
            biodiversity["artifact_admission_status"],
            "rejected_incomplete_public_evidence",
        )
        self.assertIn("0 of 2", self.registry)
        self.assertIn("zero of two", self.main)
        self.assertIn("zero of two", self.methods)
        self.assertIn("0 of 7", self.registry)
        self.assertIn("zero of seven", self.main)
        self.assertIn("0 of 7", self.methods)

    def test_coral_stays_bundled_external_benchmark(self):
        coral = self.sectors["coral_reef_residual_services"]
        self.assertEqual(coral["published_blue_scc_corals_nonmarket_use_usd_per_tco2"], 2.46)
        self.assertEqual(coral["service_bundle_count"], 8)
        self.assertFalse(coral["transfer_promoted"])
        for document in (self.registry, self.main, self.methods):
            self.assertIn("$2.46", document)

    def test_municipal_water_remains_audited_gap(self):
        water = self.sectors["municipal_water_supply"]
        self.assertEqual(water["candidates_screened"], 3)
        self.assertEqual(water["candidates_passing_all_seven_gates"], 0)
        self.assertFalse(water["lead_candidate_marginal_pulse_compatible"])
        self.assertFalse(water["lead_candidate_municipal_only_welfare_released"])
        self.assertIn("0 of 3", self.registry)
        self.assertIn("Zero of three", self.main)
        self.assertIn("zero of three", self.methods)

    def test_epa_component_net_gap_and_closed_gates_match_claim_surfaces(self):
        ozone = self.sectors["surface_ozone_health"]
        pm25 = self.sectors["nonwildfire_meteorological_pm25_health"]
        expected_gap = -26.810218031095513
        self.assertAlmostEqual(
            ozone["released_net_minus_component_sum_usd_per_tco2"], expected_gap
        )
        self.assertAlmostEqual(
            pm25["released_net_minus_component_sum_usd_per_tco2"], expected_gap
        )
        self.assertTrue(ozone["model_specific_gap_nonzero"])
        self.assertTrue(all(value is False for value in ozone["promotion_gates"].values()))
        self.assertTrue(all(value is False for value in pm25["promotion_gates"].values()))
        for document in (self.registry, self.main, self.methods):
            self.assertIn("-$26.810218", document)


if __name__ == "__main__":
    unittest.main()

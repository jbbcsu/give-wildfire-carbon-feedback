import importlib.util
import unittest
from pathlib import Path

import pandas as pd


MODULE_PATH = Path(__file__).with_name("build_us_two_stage_regional_heterogeneity.py")
SPEC = importlib.util.spec_from_file_location("two_stage_heterogeneity", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class TwoStageHeterogeneityTests(unittest.TestCase):
    def test_nonzero_sign_rule(self):
        self.assertTrue(MODULE.same_nonzero_sign(pd.Series([-2.0, -1.0, -0.1])))
        self.assertTrue(MODULE.same_nonzero_sign(pd.Series([0.1, 1.0, 2.0])))
        self.assertFalse(MODULE.same_nonzero_sign(pd.Series([-1.0, 1.0])))
        self.assertFalse(MODULE.same_nonzero_sign(pd.Series([0.0, 1.0])))

    def test_state_summary_fails_closed_when_upstream_gates_fail(self):
        records = []
        for state in [f"A{index}" for index in range(10)]:
            for model, slope in zip(MODULE.MODELS, [-2.0, 1.0, -1.0], strict=True):
                for practice in MODULE.PRACTICES:
                    records.append({
                        "model": model,
                        "practice": practice,
                        "state": state,
                        "counties": 4,
                        "mean_crop_season_precip_slope_mm_per_k": slope,
                        "estimate_percent_yield_per_k": slope / 10,
                        "spatially_robust_excludes_zero": True,
                    })
        stage2 = pd.DataFrame([
            {"practice": practice, "family": "quantity", "all_stage2_association_gates_pass": value}
            for practice, value in (("irrigated", True), ("non_irrigated", False))
        ])
        output = MODULE.state_diagnostic_rows(pd.DataFrame(records), stage2, False)
        self.assertFalse(output.linked_chain_promoted.any())
        self.assertFalse(output.climate_slope_same_nonzero_sign.any())
        self.assertFalse(output.stage1_validated_multi_model_gate_pass.any())


if __name__ == "__main__":
    unittest.main()

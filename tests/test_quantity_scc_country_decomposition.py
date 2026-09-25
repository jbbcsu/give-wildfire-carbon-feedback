from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from decompose_quantity_scc_by_country import summarize_country_components


class CountrySummaryTest(unittest.TestCase):
    def test_missing_country_model_uses_fixed_model_denominator(self) -> None:
        components = pd.DataFrame(
            {
                "climate_model": ["m1", "m2", "m1"],
                "iso3": ["AAA", "AAA", "BBB"],
                "partial_scc_usd2020_per_tco2": [-2.0, 4.0, 6.0],
            }
        )
        summary = summarize_country_components(components, ["m1", "m2"])
        values = summary.set_index("iso3")

        self.assertEqual(values.loc["AAA", "equal_model_mean_usd2020_per_tco2"], 1.0)
        self.assertEqual(values.loc["AAA", "climate_models_with_slope"], 2)
        self.assertEqual(values.loc["BBB", "equal_model_mean_usd2020_per_tco2"], 3.0)
        self.assertEqual(values.loc["BBB", "climate_model_min_usd2020_per_tco2"], 0.0)
        self.assertEqual(values.loc["BBB", "climate_models_with_slope"], 1)
        self.assertEqual(
            summary.equal_model_mean_usd2020_per_tco2.sum(),
            components.partial_scc_usd2020_per_tco2.sum() / 2,
        )


if __name__ == "__main__":
    unittest.main()

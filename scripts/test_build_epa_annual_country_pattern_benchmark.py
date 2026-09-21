#!/usr/bin/env python3
"""Synthetic invariants for the EPA country-pattern benchmark."""
import numpy as np
import pandas as pd

from build_epa_annual_country_pattern_benchmark import summarize_country


def main() -> None:
    values = np.arange(-13.0, 13.0)
    frame = pd.DataFrame({"patterns.area": values,
                          "name": ["Example"] * 26,
                          "continent": ["Test"] * 26})
    result = summarize_country(frame)
    assert result["available_models"] == 26
    assert result["missing_models"] == 0
    assert result["minimum_mm_per_year_per_k"] == -13
    assert result["maximum_mm_per_year_per_k"] == 12
    assert result["median_mm_per_year_per_k"] == -0.5
    assert result["positive_model_fraction"] == 12 / 26
    assert result["negative_model_fraction"] == 13 / 26
    print("EPA country-pattern synthetic summary checks passed")


if __name__ == "__main__":
    main()

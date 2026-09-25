#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.hultgren_rice_response import PublishedRiceEstimate, RiceBasis


def terms() -> list[str]:
    base = ["gdd", "kdd"]
    base += [f"prcp_poly_{power}_bin{phase}" for power in (1, 2) for phase in (1, 2, 3)]
    base += ["tmin"]
    result: list[str] = []
    for variable in base:
        result.append(variable)
        result.extend(
            f"c.{variable}#c.{moderator}"
            for moderator in ("ln_gdppc", "irrigated_share", "lr_tmax_crop")
        )
        cap = "prcp" if variable.startswith("prcp") else variable
        result.append(f"c.{variable}#c.pbarcut_{cap}")
    return result + ["_cons"]


def basis(rainfall_shift: float = 0.0) -> RiceBasis:
    return RiceBasis(
        gdd=900.0,
        kdd=12.0,
        prcp_poly_1_bins=(200.0 + rainfall_shift, 300.0, 400.0),
        prcp_poly_2_bins=(20_000.0 + 200.0 * rainfall_shift, 35_000.0, 60_000.0),
        tmin=110.0,
        ln_gdppc=9.0,
        irrigated_share=0.4,
        lr_tmax_crop=25.0,
        lr_prcp_crop=400.0,
    )


def main() -> None:
    ordered_terms = terms()
    assert len(ordered_terms) == 46 and len(set(ordered_terms)) == 46
    primitives = basis().primitive_values()
    assert primitives["pbarcut_gdd"] == 200.0
    assert primitives["pbarcut_kdd"] == 300.0
    assert primitives["pbarcut_prcp"] == 250.0
    assert primitives["pbarcut_tmin"] == 175.0

    with tempfile.TemporaryDirectory() as directory:
        directory_path = Path(directory)
        coefficients_path = directory_path / "coefficients.csv"
        covariance_path = directory_path / "covariance.csv"
        coefficients = np.arange(1, 47, dtype=float) / 1_000_000_000.0
        with coefficients_path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["index", "term", "estimate"])
            writer.writeheader()
            for index, (term, coefficient) in enumerate(
                zip(ordered_terms, coefficients, strict=True), start=1
            ):
                writer.writerow({"index": index, "term": term, "estimate": coefficient})
        with covariance_path.open("w", newline="") as stream:
            fields = ["row_index", "column_index", "row_term", "column_term", "covariance"]
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for row, row_term in enumerate(ordered_terms, start=1):
                for column, column_term in enumerate(ordered_terms, start=1):
                    writer.writerow(
                        {
                            "row_index": row,
                            "column_index": column,
                            "row_term": row_term,
                            "column_term": column_term,
                            "covariance": 1.0 if row == column else 0.0,
                        }
                    )
        estimate = PublishedRiceEstimate.from_exports(coefficients_path, covariance_path)
        baseline, comparison = basis(), basis(1.0)
        actual = estimate.contrast(baseline, comparison)
        delta = comparison.design_vector(ordered_terms) - baseline.design_vector(ordered_terms)
        assert np.isclose(actual["delta_log_yield"], delta @ coefficients)
        assert np.isclose(actual["coefficient_only_standard_error"], np.linalg.norm(delta))
        zero = estimate.contrast(baseline, baseline)
        assert zero["delta_log_yield"] == 0.0
        assert zero["coefficient_only_standard_error"] == 0.0
    print("published rice response algebra tests passed")


if __name__ == "__main__":
    main()

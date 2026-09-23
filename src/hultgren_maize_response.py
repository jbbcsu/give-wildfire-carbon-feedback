"""Strict algebra for the published Hultgren et al. maize estimate.

This module evaluates an already-constructed weather basis. It deliberately
does not infer how primitive daily rainfall maps into the published phase
polynomials and does not supply baseline moderator values, future climate,
damages, or an SCC calculation.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class MaizeBasis:
    gdd: float
    kdd: float
    prcp_poly_1_bins: tuple[float, float, float]
    prcp_poly_2_bins: tuple[float, float, float]
    ln_gdppc: float
    irrigated_share: float
    lr_tmax_crop: float
    lr_prcp_crop: float

    def primitive_values(self) -> dict[str, float]:
        values = {
            "gdd": self.gdd,
            "kdd": self.kdd,
            "ln_gdppc": self.ln_gdppc,
            "irrigated_share": self.irrigated_share,
            "lr_tmax_crop": self.lr_tmax_crop,
            "pbarcut_gdd": min(self.lr_prcp_crop, 200.0),
            "pbarcut_kdd": min(self.lr_prcp_crop, 100.0),
            "pbarcut_prcp": min(self.lr_prcp_crop, 250.0),
            "_cons": 1.0,
        }
        for index, value in enumerate(self.prcp_poly_1_bins, start=1):
            values[f"prcp_poly_1_bin{index}"] = value
        for index, value in enumerate(self.prcp_poly_2_bins, start=1):
            values[f"prcp_poly_2_bin{index}"] = value
        if not all(math.isfinite(value) for value in values.values()):
            raise ValueError("maize basis contains a nonfinite value")
        if not 0.0 <= self.irrigated_share <= 1.0:
            raise ValueError("irrigated_share must be in [0, 1]")
        if self.lr_prcp_crop < 0.0:
            raise ValueError("lr_prcp_crop must be nonnegative")
        return values

    def design_vector(self, terms: list[str]) -> np.ndarray:
        primitives = self.primitive_values()
        result = []
        for term in terms:
            factors = [factor.removeprefix("c.") for factor in term.split("#")]
            missing = [factor for factor in factors if factor not in primitives]
            if missing:
                raise ValueError(f"unsupported published term {term!r}: {missing}")
            result.append(math.prod(primitives[factor] for factor in factors))
        return np.asarray(result, dtype=float)


@dataclass(frozen=True)
class PublishedEstimate:
    terms: list[str]
    coefficients: np.ndarray
    covariance: np.ndarray

    @classmethod
    def from_exports(cls, coefficients_path: Path, covariance_path: Path) -> "PublishedEstimate":
        with coefficients_path.open(newline="") as stream:
            coefficient_rows = list(csv.DictReader(stream))
        indices = [int(row["index"]) for row in coefficient_rows]
        if indices != list(range(1, len(indices) + 1)):
            raise ValueError("coefficient indices are not consecutive")
        terms = [row["term"] for row in coefficient_rows]
        if len(terms) != 49 or len(set(terms)) != 49 or terms[-1] != "_cons":
            raise ValueError("published coefficient support differs from 49 unique terms ending in _cons")
        coefficients = np.asarray([float(row["estimate"]) for row in coefficient_rows])

        with covariance_path.open(newline="") as stream:
            covariance_rows = list(csv.DictReader(stream))
        covariance = np.full((len(terms), len(terms)), np.nan)
        for row in covariance_rows:
            i, j = int(row["row_index"]) - 1, int(row["column_index"]) - 1
            if row["row_term"] != terms[i] or row["column_term"] != terms[j]:
                raise ValueError("covariance term/index mismatch")
            if math.isfinite(covariance[i, j]):
                raise ValueError("duplicate covariance entry")
            covariance[i, j] = float(row["covariance"])
        if not np.isfinite(coefficients).all() or not np.isfinite(covariance).all():
            raise ValueError("estimate export contains nonfinite values")
        if not np.allclose(covariance, covariance.T, atol=1e-12, rtol=0.0):
            raise ValueError("covariance matrix is not symmetric")
        if np.any(np.diag(covariance) < 0.0):
            raise ValueError("covariance matrix has a negative diagonal")
        return cls(terms=terms, coefficients=coefficients, covariance=covariance)

    def linear_predictor(self, basis: MaizeBasis) -> float:
        return float(basis.design_vector(self.terms) @ self.coefficients)

    def contrast(self, baseline: MaizeBasis, comparison: MaizeBasis) -> dict[str, float]:
        delta_design = comparison.design_vector(self.terms) - baseline.design_vector(self.terms)
        delta_log_yield = float(delta_design @ self.coefficients)
        # Explicit elementwise quadratic form avoids platform BLAS warnings on
        # exactly zero contrasts with large interaction-basis magnitudes.
        variance = float(np.sum(
            np.multiply.outer(delta_design, delta_design) * self.covariance,
            dtype=np.float64,
        ))
        if variance < -1e-10:
            raise ValueError(f"contrast variance is materially negative: {variance}")
        variance = max(variance, 0.0)
        return {
            "delta_log_yield": delta_log_yield,
            "exact_percent_yield_change": 100.0 * math.expm1(delta_log_yield),
            "coefficient_only_standard_error": math.sqrt(variance),
        }

#!/usr/bin/env python3
"""Independent UBPWM generalized-logistic fitting used by the SPEI pipeline.

The three-parameter distribution called ``log-Logistic`` by the SPEI R
package is the generalized logistic (GLO) distribution in Hosking's L-moment
parameterization.  This module implements the equations directly from the
published PWM/L-moment definitions and the documented GLO quantile function;
it does not contain or translate code from the GPL-licensed SPEI package.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from statistics import NormalDist

import numpy as np


CALIBRATION_OBSERVATIONS = 30
CDF_CLIP_EPSILON = 1e-12
# lmom::pelglo uses the ordinary-logistic limit at this tolerance.  Matching
# that documented reference behavior avoids unstable cancellation around zero.
SMALL_SHAPE = 1e-6
FIT_STATUS_VALID = 0
FIT_STATUS_MISSING_CALIBRATION = 1
FIT_STATUS_DEGENERATE = 2
FIT_STATUS_INVALID_SHAPE = 3
FIT_STATUS_NUMERICAL_FAILURE = 4
FIT_STATUS_LABELS = {
    FIT_STATUS_VALID: "valid",
    FIT_STATUS_MISSING_CALIBRATION: "missing_calibration",
    FIT_STATUS_DEGENERATE: "degenerate",
    FIT_STATUS_INVALID_SHAPE: "invalid_shape",
    FIT_STATUS_NUMERICAL_FAILURE: "numerical_failure",
}
CDF_CLIP_MISSING = -9
CDF_CLIP_LOWER = -1
CDF_CLIP_NONE = 0
CDF_CLIP_UPPER = 1
_STANDARD_NORMAL = NormalDist()


class GloFitError(ValueError):
    """A classified fail-closed GLO fit error."""

    def __init__(self, message: str, status: int) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class GloParameters:
    """Location, scale, and shape in the lmom generalized-logistic convention."""

    xi: float
    alpha: float
    kappa: float
    sample_size: int
    beta0: float
    beta1: float
    beta2: float
    l1: float
    l2: float
    tau3: float


@dataclass(frozen=True)
class StandardizedValues:
    """SPEI values plus an observation-level probability clipping audit."""

    probabilities: np.ndarray
    clipped_probabilities: np.ndarray
    spei: np.ndarray
    clip_code: np.ndarray

    @property
    def lower_clip_count(self) -> int:
        return int(np.count_nonzero(self.clip_code == CDF_CLIP_LOWER))

    @property
    def upper_clip_count(self) -> int:
        return int(np.count_nonzero(self.clip_code == CDF_CLIP_UPPER))


def _finite_vector(values: object, label: str) -> np.ndarray:
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise GloFitError(f"{label} must be numeric", FIT_STATUS_NUMERICAL_FAILURE) from error
    if array.ndim != 1:
        raise GloFitError(f"{label} must be one-dimensional", FIT_STATUS_NUMERICAL_FAILURE)
    if not np.isfinite(array).all():
        raise GloFitError(
            f"{label} must contain only finite calibration values",
            FIT_STATUS_MISSING_CALIBRATION,
        )
    return array


def unbiased_probability_weighted_moments(values: object) -> tuple[float, float, float]:
    """Return unbiased beta_0, beta_1, beta_2 for an ascending sample.

    For order r, beta_r is the sample mean of x_(j) multiplied by
    choose(j-1, r) / choose(n-1, r).  Sorting is internal and stable.
    """
    sample = np.sort(_finite_vector(values, "values"), kind="mergesort")
    n = sample.size
    if n < 3:
        raise GloFitError("at least three values are required", FIT_STATUS_MISSING_CALIBRATION)
    rank = np.arange(n, dtype=np.float64)
    beta0 = float(np.mean(sample))
    beta1 = float(np.mean(sample * rank / (n - 1)))
    beta2 = float(np.mean(sample * rank * (rank - 1) / ((n - 1) * (n - 2))))
    if not np.isfinite([beta0, beta1, beta2]).all():
        raise GloFitError("PWM calculation was not finite", FIT_STATUS_NUMERICAL_FAILURE)
    return beta0, beta1, beta2


def fit_glo_ubpwm(
    values: object,
    *,
    required_observations: int = CALIBRATION_OBSERVATIONS,
) -> GloParameters:
    """Fit the three-parameter GLO by unbiased PWMs and L-moments."""
    sample = _finite_vector(values, "calibration values")
    if sample.size != required_observations:
        raise GloFitError(
            f"expected exactly {required_observations} calibration values, got {sample.size}",
            FIT_STATUS_MISSING_CALIBRATION,
        )
    beta0, beta1, beta2 = unbiased_probability_weighted_moments(sample)
    l1 = beta0
    l2 = 2.0 * beta1 - beta0
    magnitude = max(1.0, float(np.max(np.abs(sample))))
    tolerance = 64.0 * np.finfo(np.float64).eps * magnitude
    if not math.isfinite(l2) or l2 <= tolerance:
        raise GloFitError("second L-moment is zero or numerically degenerate", FIT_STATUS_DEGENERATE)
    l3 = 6.0 * beta2 - 6.0 * beta1 + beta0
    tau3 = l3 / l2
    kappa = -tau3
    if not math.isfinite(kappa) or abs(kappa) >= 1.0:
        raise GloFitError("GLO shape must be finite and strictly between -1 and 1", FIT_STATUS_INVALID_SHAPE)

    if abs(kappa) <= SMALL_SHAPE:
        # The kappa -> 0 limit is the ordinary logistic distribution.
        alpha = l2
        xi = l1
        kappa = 0.0
    else:
        sine = math.sin(math.pi * kappa)
        if not math.isfinite(sine) or sine == 0.0:
            raise GloFitError("GLO shape produced a singular fit", FIT_STATUS_INVALID_SHAPE)
        alpha = l2 * sine / (math.pi * kappa)
        xi = l1 - alpha * (1.0 / kappa - math.pi / sine)
    if not math.isfinite(xi) or not math.isfinite(alpha) or alpha <= tolerance:
        raise GloFitError("GLO location or scale is numerically invalid", FIT_STATUS_NUMERICAL_FAILURE)
    return GloParameters(
        xi=float(xi),
        alpha=float(alpha),
        kappa=float(kappa),
        sample_size=int(sample.size),
        beta0=float(beta0),
        beta1=float(beta1),
        beta2=float(beta2),
        l1=float(l1),
        l2=float(l2),
        tau3=float(tau3),
    )


def glo_cdf(values: object, parameters: GloParameters) -> np.ndarray:
    """Evaluate the GLO nonexceedance probability, including finite bounds."""
    try:
        data = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise ValueError("values must be numeric") from error
    if not all(
        (
            math.isfinite(parameters.xi),
            math.isfinite(parameters.alpha),
            math.isfinite(parameters.kappa),
            parameters.alpha > 0.0,
            abs(parameters.kappa) < 1.0,
        )
    ):
        raise ValueError("invalid GLO parameters")
    result = np.full(data.shape, np.nan, dtype=np.float64)
    finite = np.isfinite(data)
    if not finite.any():
        return result
    z = (data[finite] - parameters.xi) / parameters.alpha
    kappa = parameters.kappa
    if kappa == 0.0:
        transformed = z
        inside = np.ones(z.shape, dtype=bool)
    else:
        support_term = 1.0 - kappa * z
        inside = support_term > 0.0
        transformed = np.empty(z.shape, dtype=np.float64)
        transformed[inside] = -np.log(support_term[inside]) / kappa
        if kappa > 0.0:
            transformed[~inside] = np.inf
        else:
            transformed[~inside] = -np.inf

    probability = np.empty(transformed.shape, dtype=np.float64)
    nonnegative = transformed >= 0.0
    probability[nonnegative] = 1.0 / (1.0 + np.exp(-transformed[nonnegative]))
    exponential = np.exp(transformed[~nonnegative])
    probability[~nonnegative] = exponential / (1.0 + exponential)
    probability = np.clip(probability, 0.0, 1.0)
    result[finite] = probability
    return result


def standardize_glo(
    values: object,
    parameters: GloParameters,
    *,
    clip_epsilon: float = CDF_CLIP_EPSILON,
) -> StandardizedValues:
    """Map GLO probabilities to standard-normal scores and audit tail clipping."""
    if not math.isfinite(clip_epsilon) or not 0.0 < clip_epsilon < 0.5:
        raise ValueError("clip_epsilon must be finite and strictly between 0 and 0.5")
    probability = glo_cdf(values, parameters)
    clipped = probability.copy()
    clip_code = np.full(probability.shape, CDF_CLIP_MISSING, dtype=np.int8)
    finite = np.isfinite(probability)
    lower = finite & (probability < clip_epsilon)
    upper = finite & (probability > 1.0 - clip_epsilon)
    middle = finite & ~lower & ~upper
    clipped[lower] = clip_epsilon
    clipped[upper] = 1.0 - clip_epsilon
    clip_code[lower] = CDF_CLIP_LOWER
    clip_code[middle] = CDF_CLIP_NONE
    clip_code[upper] = CDF_CLIP_UPPER
    spei = np.full(probability.shape, np.nan, dtype=np.float64)
    if finite.any():
        spei[finite] = np.fromiter(
            (_STANDARD_NORMAL.inv_cdf(float(value)) for value in clipped[finite]),
            dtype=np.float64,
            count=int(np.count_nonzero(finite)),
        )
    return StandardizedValues(
        probabilities=probability,
        clipped_probabilities=clipped,
        spei=spei,
        clip_code=clip_code,
    )

"""Primitive weather basis for the published Hultgren maize benchmark.

This module deliberately starts after crop-calendar alignment: callers must
provide the 4--10 local growing-season monthly precipitation totals and the
daily maximum temperatures for the same season.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from .hultgren_maize_response import MaizeBasis


@dataclass(frozen=True)
class MaizeWeatherBasis:
    gdd: float
    kdd: float
    prcp_poly_1_bins: tuple[float, float, float]
    prcp_poly_2_bins: tuple[float, float, float]

    def with_moderators(
        self,
        *,
        ln_gdppc: float,
        irrigated_share: float,
        lr_tmax_crop: float,
        lr_prcp_crop: float,
    ) -> "MaizeBasis":
        """Attach declared moderators for the published 49-term response."""
        from .hultgren_maize_response import MaizeBasis

        result = MaizeBasis(
            gdd=self.gdd,
            kdd=self.kdd,
            prcp_poly_1_bins=self.prcp_poly_1_bins,
            prcp_poly_2_bins=self.prcp_poly_2_bins,
            ln_gdppc=ln_gdppc,
            irrigated_share=irrigated_share,
            lr_tmax_crop=lr_tmax_crop,
            lr_prcp_crop=lr_prcp_crop,
        )
        result.primitive_values()
        return result


def _finite(values: Iterable[float], name: str) -> tuple[float, ...]:
    result = tuple(float(value) for value in values)
    if not result or not all(isfinite(value) for value in result):
        raise ValueError(f"{name} must contain finite values")
    return result


def build_maize_weather_basis(
    monthly_precipitation_mm: Iterable[float],
    daily_tmax_c: Iterable[float],
    *,
    gdd_base_c: float = 8.0,
    kdd_threshold_c: float = 31.0,
) -> MaizeWeatherBasis:
    """Construct the source-matched maize weather basis without calendar guesses."""

    precipitation = _finite(monthly_precipitation_mm, "monthly_precipitation_mm")
    temperature = _finite(daily_tmax_c, "daily_tmax_c")
    if not 4 <= len(precipitation) <= 10:
        raise ValueError("maize crop-calendar season must contain 4 through 10 months")
    if any(value < 0 for value in precipitation):
        raise ValueError("monthly precipitation cannot be negative")
    if not gdd_base_c < kdd_threshold_c:
        raise ValueError("gdd_base_c must be below kdd_threshold_c")

    slices = (precipitation[:1], precipitation[1:4], precipitation[4:])
    linear = tuple(sum(values) for values in slices)
    quadratic = tuple(sum(value * value for value in values) for values in slices)
    gdd = sum(min(max(value - gdd_base_c, 0.0), kdd_threshold_c - gdd_base_c) for value in temperature)
    kdd = sum(max(value - kdd_threshold_c, 0.0) for value in temperature)
    return MaizeWeatherBasis(gdd, kdd, linear, quadratic)

#!/usr/bin/env python3
"""Inference primitives for synthetic validation of the frozen corn protocol.

This module accepts already residualized designs and residual vectors.  It
does not load project data, construct outcomes, or estimate a real response.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


EARTH_RADIUS_KM = 6371.0088


def _arrays(
    x: np.ndarray, residual: np.ndarray, counties: np.ndarray, years: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    design = np.asarray(x, dtype=float)
    error = np.asarray(residual, dtype=float)
    county = np.asarray(counties).astype(str)
    year = np.asarray(years)
    if design.ndim != 2 or error.ndim != 1 or len(design) != len(error):
        raise ValueError("design/residual dimensions disagree")
    if len(county) != len(error) or len(year) != len(error):
        raise ValueError("cluster/year dimensions disagree")
    if not np.isfinite(design).all() or not np.isfinite(error).all():
        raise ValueError("design and residual must be finite")
    return design, error, county, year


def county_cr1_meat(x: np.ndarray, residual: np.ndarray, counties: np.ndarray) -> np.ndarray:
    """County score meat with the frozen CR1 finite-sample correction."""
    design = np.asarray(x, dtype=float)
    error = np.asarray(residual, dtype=float)
    county = np.asarray(counties).astype(str)
    if design.ndim != 2 or error.ndim != 1 or len(design) != len(error) or len(county) != len(error):
        raise ValueError("county CR1 inputs are not aligned")
    n, k = design.shape
    codes, labels = pd.factorize(county, sort=True)
    if len(labels) <= 1 or n <= k:
        raise ValueError("county CR1 requires multiple clusters and n > k")
    scores = design * error[:, None]
    meat = np.zeros((k, k), dtype=float)
    for code in range(len(labels)):
        total = scores[codes == code].sum(axis=0)
        meat += np.outer(total, total)
    correction = (len(labels) / (len(labels) - 1)) * ((n - 1) / (n - k))
    return correction * meat


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    values = np.radians([lat1, lon1, lat2, lon2])
    phi1, lam1, phi2, lam2 = values
    dphi, dlam = phi2 - phi1, lam2 - lam1
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    return float(2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(min(1.0, a))))


def spatial_cross_county_meat(
    x: np.ndarray,
    residual: np.ndarray,
    counties: np.ndarray,
    years: np.ndarray,
    latitudes: np.ndarray,
    longitudes: np.ndarray,
    cutoff_km: float,
) -> np.ndarray:
    """Same-year ordered-pair Bartlett score addition, excluding same county."""
    design, error, county, year = _arrays(x, residual, counties, years)
    latitude = np.asarray(latitudes, dtype=float)
    longitude = np.asarray(longitudes, dtype=float)
    if len(latitude) != len(error) or len(longitude) != len(error):
        raise ValueError("coordinate dimensions disagree")
    if not np.isfinite(latitude).all() or not np.isfinite(longitude).all():
        raise ValueError("coordinates must be finite")
    if cutoff_km <= 0 or not np.isfinite(cutoff_km):
        raise ValueError("cutoff must be finite and positive")
    scores = design * error[:, None]
    meat = np.zeros((design.shape[1], design.shape[1]), dtype=float)
    for value in np.unique(year):
        positions = np.flatnonzero(year == value)
        for left_position in range(len(positions)):
            i = positions[left_position]
            for right_position in range(left_position + 1, len(positions)):
                j = positions[right_position]
                if county[i] == county[j]:
                    continue
                distance = haversine_km(
                    latitude[i], longitude[i], latitude[j], longitude[j]
                )
                weight = max(1.0 - distance / cutoff_km, 0.0)
                if weight:
                    meat += weight * (
                        np.outer(scores[i], scores[j]) + np.outer(scores[j], scores[i])
                    )
    return meat


def county_plus_spatial_covariance(
    x: np.ndarray,
    residual: np.ndarray,
    counties: np.ndarray,
    years: np.ndarray,
    latitudes: np.ndarray,
    longitudes: np.ndarray,
    cutoff_km: float,
) -> np.ndarray:
    """Frozen county-CR1 plus contemporaneous cross-county spatial sandwich."""
    design = np.asarray(x, dtype=float)
    gram = np.einsum("ni,nj->ij", design, design, optimize=False)
    if np.linalg.matrix_rank(gram) != gram.shape[0]:
        raise ValueError("residualized design is not full rank")
    bread = np.linalg.inv(gram)
    meat = county_cr1_meat(design, residual, counties)
    meat += spatial_cross_county_meat(
        design, residual, counties, years, latitudes, longitudes, cutoff_km
    )
    covariance = np.einsum(
        "ij,jk,kl->il", bread, meat, bread, optimize=False
    )
    return (covariance + covariance.T) / 2


def contrast_standard_error(covariance: np.ndarray, contrast: np.ndarray) -> float:
    cov = np.asarray(covariance, dtype=float)
    vector = np.asarray(contrast, dtype=float)
    variance = float(np.einsum("i,ij,j->", vector, cov, vector, optimize=False))
    if not np.isfinite(variance) or variance < 0:
        raise ValueError("contrast variance is nonfinite or negative")
    return float(np.sqrt(variance))


def influence_gate(
    full_estimate: float,
    full_standard_error: float,
    omission_estimates: np.ndarray,
    maximum_absolute_dfbeta: float,
) -> dict[str, object]:
    estimates = np.asarray(omission_estimates, dtype=float)
    if full_standard_error <= 0 or not np.isfinite(full_standard_error):
        raise ValueError("full-sample standard error must be finite and positive")
    if not np.isfinite(estimates).all() or len(estimates) == 0:
        raise ValueError("omission estimates must be nonempty and finite")
    dfbeta = np.abs(estimates - full_estimate) / full_standard_error
    sign_required = abs(full_estimate) >= full_standard_error
    sign_pass = not sign_required or bool(np.all(np.sign(estimates) == np.sign(full_estimate)))
    return {
        "maximum_absolute_dfbeta": float(dfbeta.max()),
        "dfbeta_pass": bool(dfbeta.max() <= maximum_absolute_dfbeta),
        "sign_check_required": sign_required,
        "sign_pass": sign_pass,
        "all_pass": bool(dfbeta.max() <= maximum_absolute_dfbeta and sign_pass),
    }


def terminal_stability_gate(
    development_estimate: float,
    development_standard_error: float,
    terminal_estimate: float,
    terminal_standard_error: float,
    maximum_standardized_difference: float,
) -> dict[str, object]:
    standard_errors = np.asarray(
        [development_standard_error, terminal_standard_error], dtype=float
    )
    if (standard_errors <= 0).any() or not np.isfinite(standard_errors).all():
        raise ValueError("split standard errors must be finite and positive")
    denominator = float(np.sqrt(np.sum(standard_errors**2)))
    standardized = abs(terminal_estimate - development_estimate) / denominator
    sign_required = (
        abs(development_estimate) >= development_standard_error
        or abs(terminal_estimate) >= terminal_standard_error
    )
    sign_pass = not sign_required or np.sign(development_estimate) == np.sign(terminal_estimate)
    return {
        "absolute_standardized_difference": float(standardized),
        "difference_pass": bool(standardized <= maximum_standardized_difference),
        "sign_check_required": bool(sign_required),
        "sign_pass": bool(sign_pass),
        "all_pass": bool(standardized <= maximum_standardized_difference and sign_pass),
    }

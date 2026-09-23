#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.hultgren_maize_weather import build_maize_weather_basis


def main() -> None:
    basis = build_maize_weather_basis([1, 2, 3, 4, 5, 6], [5, 8, 20, 31, 35])
    assert basis.prcp_poly_1_bins == (1.0, 9.0, 11.0)
    assert basis.prcp_poly_2_bins == (1.0, 29.0, 61.0)
    assert basis.gdd == 58.0
    assert basis.kdd == 4.0
    response_basis = basis.with_moderators(
        ln_gdppc=9.0,
        irrigated_share=0.25,
        lr_tmax_crop=24.0,
        lr_prcp_crop=300.0,
    )
    assert response_basis.prcp_poly_2_bins == (1.0, 29.0, 61.0)
    assert response_basis.primitive_values()["pbarcut_prcp"] == 250.0
    try:
        basis.with_moderators(
            ln_gdppc=9.0,
            irrigated_share=1.1,
            lr_tmax_crop=24.0,
            lr_prcp_crop=300.0,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("invalid moderator combination accepted")
    for rainfall in ([1, 2, 3], [1] * 11, [1, 2, 3, -1]):
        try:
            build_maize_weather_basis(rainfall, [20])
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid rainfall accepted: {rainfall}")
    print("published maize primitive-weather basis tests passed")


if __name__ == "__main__":
    main()

"""Synthetic physical-domain tests for the static-grid acquisition gate."""
import math

import numpy as np

from acquire_cmip6_native_cell_area import checked_area


def fails(area, lat, lon):
    try:
        checked_area(area, lat, lon)
    except ValueError:
        return
    raise AssertionError("invalid cell area unexpectedly accepted")


def main():
    sphere = 4 * math.pi * 6371000.0**2
    lat = np.array([-45.0, 45.0])
    lon = np.array([90.0, 270.0])
    area = np.full((2, 2), sphere / 4)
    assert math.isclose(checked_area(area, lat, lon), sphere)
    fails(area[:1], lat, lon)
    bad = area.copy(); bad[0, 0] = 0
    fails(bad, lat, lon)
    bad = area.copy(); bad[0, 0] = np.nan
    fails(bad, lat, lon)
    fails(area * 0.95, lat, lon)
    print("native area synthetic checks pass")


if __name__ == "__main__":
    main()

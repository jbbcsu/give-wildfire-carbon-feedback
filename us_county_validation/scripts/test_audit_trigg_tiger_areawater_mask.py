#!/usr/bin/env python3
"""Synthetic checks for fractional TIGER area-water allocation."""

from shapely.geometry import box

from audit_trigg_tiger_areawater_mask import fractional_water_area


target = box(0, 0, 2, 1)
features = [(box(0, 0, 1, 1), 0.75), (box(1, 0, 2, 1), 0.25)]
assert fractional_water_area(target, features) == 1.0
assert fractional_water_area(box(0, 0, 0.5, 1), features) == 0.375
assert fractional_water_area(box(3, 3, 4, 4), features) == 0.0
print("Trigg TIGER fractional-water synthetic test passed")

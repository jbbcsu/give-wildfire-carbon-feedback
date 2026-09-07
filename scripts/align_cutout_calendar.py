"""Exact coordinate selection for server-cutout climate; never interpolates."""
import numpy as np


def align_calendar(calendar, climate):
    """Select calendar coordinates in climate order, rejecting ambiguous grids.

    Latitude indices in a cutout refer to the cutout, not the full calendar.
    No nearest-neighbor matching, longitude wrapping, or implicit regridding
    is allowed. Selection is label-based and must preserve exact coordinates.
    """
    for axis in ('lat', 'lon'):
        for label, obj in (('calendar', calendar), ('climate', climate)):
            if axis not in obj.coords or obj[axis].dims != (axis,):
                raise ValueError(f'{label} needs one-dimensional {axis} coordinates')
            values = obj[axis].values
            if not len(values) or not np.isfinite(values).all():
                raise ValueError(f'{label} has empty/nonfinite {axis}')
            if len(np.unique(values)) != len(values):
                raise ValueError(f'{label} has duplicate {axis}')
        if not np.isin(climate[axis].values, calendar[axis].values).all():
            raise ValueError(f'climate {axis} absent from calendar; no regridding allowed')
    selected = calendar.sel(lat=climate.lat.values, lon=climate.lon.values)
    for axis in ('lat', 'lon'):
        if not np.array_equal(selected[axis].values, climate[axis].values):
            raise ValueError(f'{axis} ordering mismatch')
    for name in ('planting_day', 'maturity_day'):
        if name not in selected or selected[name].dims != ('lat', 'lon'):
            raise ValueError(f'calendar {name} must have lat, lon dimension order')
    return selected

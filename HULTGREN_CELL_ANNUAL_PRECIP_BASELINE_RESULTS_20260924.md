# Maize-cell annual precipitation baseline for the quantity-only pulse benchmark

## Result

A bounded streaming calculation now supplies the positive annual-rainfall
denominator needed to translate the validated EPA/FAIR country annual change
into proportional monthly changes on the Hultgren maize grid. The calculation
uses the resident GSWP3-W5E5 daily precipitation files for 1981--2010 and the
exact 23,654 unique cells in the independently validated matched-support
common-price maize weights.

All 10,957 daily steps across 30 complete calendar years were processed with
zero missing daily cell pairs. Mean annual precipitation is positive at every
represented cell, ranging from 1.026 to 9,636.675 mm yr-1. The compact output
is 972,933 bytes, below the registered 64 MiB owned-output ceiling. The build
completed at 175.8 MiB sampled peak process-group RSS under the 512 MiB cap
and 130 GiB free-disk floor.

## Validation

The receipt pins the SHA-512 of all three multi-gigabyte daily source files,
the common-price support hash and the compact output hash. A separately coded
validator rechecks every source and output hash, all 23,654 unique keys and
all finite output values. It then re-reads daily precipitation for five fixed
key-order sentinel cells and independently reconstructs 150 cell-year totals.
The mean, sample standard deviation, minimum and maximum agree with the saved
output to zero machine discrepancy at every sentinel. This is a sentinel
arithmetic validation, not a second full-cell calculation.

## Interpretation boundary

This closes only the annual-baseline input required by the preregistered
uniform-absolute-change quantity benchmark. It does not estimate marginal
rainfall, crop response, damages or SCC. GSWP3-W5E5 is not the source PEEPS
country mask and is not the authors' GMFD weather product. The benchmark must
continue to disclose that the published EPA country mean change is imposed
uniformly in absolute annual millimetres across represented crop cells while
each cell's baseline monthly shares are held fixed.

Artifacts:

- Builder: `scripts/build_hultgren_cell_annual_precip_climatology.py`
- Unit test: `scripts/test_build_hultgren_cell_annual_precip_climatology.py`
- Validator: `scripts/validate_hultgren_cell_annual_precip_climatology.py`
- Receipt: `data/provenance/hultgren_cell_annual_precip_climatology_20260924.json`
- Validation: `data/provenance/hultgren_cell_annual_precip_climatology_validation_20260924.json`


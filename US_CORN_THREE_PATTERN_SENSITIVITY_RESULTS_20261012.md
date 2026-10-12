# Three-pattern U.S. corn climate-response sensitivity

## Purpose

The published PEEPS MPI pattern implies a substantial non-irrigated U.S. corn
penalty, but one climate pattern cannot characterize uncertainty. This
sensitivity applies the same frozen U.S. response and crop-season integration
to three monthly precipitation patterns:

1. author-published PEEPS MPI-ESM1-2-HR SSP5-8.5 slopes;
2. project-fitted PEEPS-style GFDL-ESM4 SSP5-8.5 slopes; and
3. project-fitted PEEPS-style IPSL-CM6A-LR SSP5-8.5 slopes.

The GFDL and IPSL coefficient algebra and source bindings were independently
audited, but their out-of-scenario holdout improvements were small and their
raw fitted rainfall levels can become negative. This sensitivity uses slopes
only on observed positive rainfall baselines. The three patterns are not a
homogeneous or probability-weighted climate ensemble.

## Climate-pattern spread

Equal-county crop-season precipitation slopes on the selected 361-county
support are:

| Pattern | Mean mm/K | Counties drying | Counties wetting |
|---|---:|---:|---:|
| Published MPI | -25.20 | 349 | 12 |
| Project GFDL fit | +3.68 | 142 | 219 |
| Project IPSL fit | -5.66 | 259 | 102 |

Only 84 of 361 counties have the same nonzero slope sign in all three
patterns. This sign disagreement is a climate-response uncertainty, not a
yield-model uncertainty.

## Yield transport

Each pattern is integrated over exact county crop-season dates and evaluated
through exactly the same historical response. Equal-county fitted yield
responses per degree of warming are:

| Pattern | Non-irrigated | 500 km interval | Irrigated | 500 km interval |
|---|---:|---:|---:|---:|
| Published MPI | -2.32% | -2.82% to -1.82% | +0.03% | -0.14% to +0.21% |
| Project GFDL fit | +0.58% | +0.44% to +0.72% | +0.03% | -0.01% to +0.07% |
| Project IPSL fit | -0.68% | -0.84% to -0.53% | -0.02% | -0.07% to +0.03% |

The descriptive equal-pattern mean non-irrigated response is -0.81%/K, with a
range from -2.32% to +0.58%/K. This mean is not promoted: the pattern set is
small and heterogeneous, and the two project fits are structural
sensitivities rather than validated substitutes for published coefficients.

## Interpretation

This result identifies a major reason the precipitation SCC remains uncertain.
The U.S. historical moisture response is economically meaningful, but the sign
and magnitude of warming-driven crop-season rainfall differ substantially
across climate patterns. Sampling uncertainty around a given response is much
smaller than the between-pattern climate spread.

Therefore, a defensible paper should report:

- the published MPI calculation as the literature-based benchmark;
- GFDL/IPSL as transparent structural sensitivities;
- the full between-pattern sign and magnitude spread; and
- a separate multi-model/downscaled validation before any central U.S. damage
  or SCC claim.

The calculation still omits daily dry spells, PDSI, extremes, additional
crops, nationally representative support, production weights, welfare, and
adaptation. It does not open national yield, damage, or SCC gates.

## Reproduction

- `us_county_validation/scripts/build_us_corn_three_pattern_sensitivity.py`
- `data/provenance/us_corn_three_pattern_sensitivity_20261012.json`
- State table (gitignored):
  `data/interim/us_corn_three_pattern_state_20261012.csv`

The bounded run peaked at 194.9 MB, below the 512 MiB ceiling; all one-degree
seasonal rainfall perturbations remain nonnegative on observed baselines.

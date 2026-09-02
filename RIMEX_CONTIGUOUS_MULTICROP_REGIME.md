# Contiguous RIME-X multi-crop and calendar-regime validation

This preregistration fixes the next use of the already validated contiguous
GFDL-ESM4 `r1i1p1f1` SSP1-2.6 daily `pr` and `tas` pilot before constructing
the new feature tables. It expands the bounded latitude rows 100--101 from
maize/rainfed to the complete Cartesian product of maize, soybean, first- and
second-season rice, spring wheat, and winter wheat with rainfed (`noirr`) and
fully irrigated (`firr`) GGCMI Phase 3 calendars.

The source period is 2031--2060. Feature harvest years are fixed at 2032--2059
and the 21-year centered outputs at 2042--2049. Calendar hashes and bounded
valid-cell counts are locked in
`config/isimip3b_rimex_contiguous_multicrop_regime_v1.toml`. The 12 cells imply
214,928 expected seasonal rows before centering and 61,408 afterward; second-
season rice has lower spatial support explicitly rather than being silently
filled.

The validation must require exact annual sequences, exact season/stage
reconciliation, common same-realization GMST, physical rainfall constraints,
and all 12 registered crop/calendar cells. Contrasts between `firr` and
`noirr` are calendar sensitivity checks only. They are not irrigation treatment
effects because the climate inputs and available yield outcomes do not identify
such an effect.

This work expands daily-feature engineering support only. It does not supply
new ESMs or scenarios, meet the 51-template joint-dependence minimum, estimate
a crop response, or authorize damages or SCC use.

# GFDL future SPEI crop-window pilot protocol

Registered before crop-window results were computed on September 19, 2026.

## Purpose

Test whether the independently validated 512-cell GFDL monthly SPEI boundary
pilot can be mapped to fixed rainfed and irrigated maize/soy crop calendars
without changing historical feature definitions. This is an outcome-free
engineering test, not a future yield, damage, or SCC estimate.

## Locked design

- Input cube: the validated GFDL boundary output with SSP1-2.6, SSP3-7.0,
  SSP5-8.5; monthly 2011--2020 SPEI at 1/3/6-month scales; 512 frozen native
  crop-support cells; observational 1982--2011 parameters with no future refit.
- Candidate support: unique crop/cell pairs in frozen sparse block zero. Do not
  infer new cultivated cells from climate availability.
- Crops: maize (`mai`) and soybean (`soy`).
- Harvest years: 2015--2020 under fixed GGCMI Phase 3 `2015soc` rainfed and
  fully irrigated calendars.
- Windows: full season, three fixed proportional stages (0--30%, 30--70%,
  70--100%), and 90 days before planting.
- Irrigation allocation: compute each positive-share regime first, then combine
  with the already validated fixed MIRCA-OS v2 area shares. Do not use outcomes
  or future climate to change shares.
- Monthly boundary approximation: day-weight each monthly SPEI value over the
  exact overlap with the crop window; retain the predeclared month-end
  sensitivity separately.

## Gates and checks

1. Rehash the input cube, crop-support partition, calendar files, weights, and
   upstream validation receipt before construction.
2. Preserve scenario, crop, coordinate, harvest year, window, scale, and
   irrigation keys. Fail on duplicate keys or incomplete positive-share sums.
3. Emit explicit non-complete statuses; do not impute, drop one regime and
   renormalize, or convert a missing index to zero.
4. Independently verify every combined value against the saved regime values
   and fixed shares, all key counts and statuses, and a fixed sample directly
   against the monthly cube and crop-calendar dates.
5. Report only support/status counts and descriptive unweighted feature means.
   Scenario contrasts are not forcing effects because these are divergent raw
   scenario weather paths, not paired marginal pulses.

## Resource constraints

One process at a time, sampled RSS at most 512 MiB, owned output at most 64 MiB,
free disk at least 130 GiB, and log at most 2 MiB. No downloads or raw-data
changes.

## Closed uses

The pilot cannot select a drought-response family, estimate crop loss, infer
adaptation, monetize damage, or enter GIVE/SCC. Those uses require the full
multi-ESM later-century exposure matrix, the prespecified yield-response gates,
and paired marginal climate accounting.

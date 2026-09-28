# U.S. sorghum and cotton fixed-calendar protocol

## Purpose

Establish whether the newly acquired paired-practice outcomes can receive
source-pinned state-level growing-season dates before any weather join or
response estimation. This is a feature-construction gate, not an empirical
result.

## Frozen source and rules

- Source: USDA NASS, *Field Crops Usual Planting and Harvesting Dates*
  (October 2010, Agricultural Handbook 628), locally pinned at the checksum in
  `data/provenance/nass_field_crop_calendar_2010.toml`.
- Tables: All Cotton, PDF page 11 (17 states), and Sorghum for Grain, PDF page
  23 (14 states).
- Primary window: floor midpoint of the published most-active planting range
  through floor midpoint of the most-active harvesting range.
- Broad sensitivity: published planting begin through published harvest end.
- Harvest-year convention: the year containing harvest onset and the central
  harvest interval. A published terminal tail that wraps into January is kept
  in the following calendar year. We do not force all eight statewide bounds
  into one sequential phenology: for geographically diverse Texas sorghum,
  the published statewide planting tail overlaps the harvest onset.
- The dates are fixed usual dates, not realized annual phenology. The stage
  split remains an equal-duration engineering proxy and is not crop phenology.

## Gates

Every outcome state must have one source definition and exactly two calendar
roles for every supported harvest year. Constructed season dates must be
ordered, may end no later than the following year, and all month/day values
must remain fixed across years. The paired irrigated and non-irrigated outcomes receive
the same crop/state calendar; this does not identify irrigation-specific
phenology. Weather joins, response estimation, causal interpretation, damage,
and SCC use remain unauthorized.

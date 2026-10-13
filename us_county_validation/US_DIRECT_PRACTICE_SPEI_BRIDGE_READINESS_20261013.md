# Direct-practice corn SPEI bridge readiness

## Question

Can the already validated historical GSWP3-W5E5 SPEI archive and future
five-ESM SPEI cubes be aggregated to the exact 361 counties in the frozen
non-irrigated corn design, using the same NASS calendar, without reading crop
outcomes?

## Decision

Not yet. The climate and calendar machinery exists, but the current SPEI cell
footprint fails the frozen 0.999 geometric-coverage rule for 10 of 361
counties. The audit therefore writes diagnostic weights and an exact missing-
cell inventory but deliberately does not construct a partial scientific panel.

The historical candidate archive contains 468 months for all 31,208 fixed
global maize/soy support cells. Its 1,123,488 distribution fits already pass
the independent construction audit. The future five-ESM by three-SSP cubes use
that same fixed cell footprint. Thus the problem is not a missing SPEI method,
calibration, or NASS calendar; it is a small but consequential spatial-support
gap.

The metadata-only sample audit also confirmed all 7,013 season starts and ends
fall in their harvest year, are ordered, and use one fixed month-day window
within each of the 10 represented states under the frozen 2010 NASS calendar.

## Exact support result

Using TIGER/Line 2019 county polygons, the ISIMIP half-degree cell boundaries,
and equal-area EPSG:5070 intersections:

- 351 counties pass coverage of at least 0.999;
- 10 counties fail;
- the minimum coverage is 0.411630;
- 11 unique native half-degree cells account for the failed counties' missing
  support.

The two largest failures are Sioux County, North Dakota (`38071`, 0.411630)
and Burleson County, Texas (`48057`, 0.420356). McKinley County, New Mexico
(`35031`) has 0.807901 coverage. The remaining seven failures range from
0.967022 to 0.998829. Exact county and native-cell records are in the ignored
audit output and summarized in the tracked provenance receipt.

The bounded audit completed with sampled peak process-group RSS of 220,332,032
bytes under the 512 MiB gate. A separate receipt validator passed 83 checks of
hashes, sample identity, coverage arithmetic, threshold decisions, normalized
weights, native index mappings, missing-cell reconstruction, all 15 independently
validated future model-scenario support bindings, and closed gates.
The synthetic fail-closed and spatial-arithmetic suite passed 12 checks.

## Blocker and next step

Historical raw GSWP3-W5E5 precipitation, minimum temperature, and maximum
temperature remain locally available, so the 11 historical cells can be
constructed with the frozen Hargreaves/GLO/1982--2011 method. That alone does
not open the bridge: the processed future cubes also omit the same cells, and
the streaming protocol deleted future temperature-extreme files after their
validated crop-footprint reductions. Those exact model/scenario extrema must
be reacquired or otherwise reconstructed under their saved source identities.

After the 11 cells exist in both eras, rerun the identical county weights,
apply the 2010 NASS corn calendar to SPEI-1/3/6, independently validate all
7,013 county-years on 361 counties, and only then consider a separately
authorized historical response validation. Direct rainfall and SPEI remain
competing models and cannot be stacked or added.

No yield value was read, no response was fit, and all projection, causal,
damage, and SCC gates remain closed.

## Reproducibility files

- frozen contract: `config/us_direct_practice_spei_bridge_readiness_v1.toml`;
- audit: `us_county_validation/scripts/audit_us_direct_practice_spei_bridge_readiness.py`;
- independent validator: `us_county_validation/scripts/validate_us_direct_practice_spei_bridge_readiness.py`;
- focused tests: `us_county_validation/scripts/test_audit_us_direct_practice_spei_bridge_readiness.py`;
- tracked provenance: `data/provenance/us_direct_practice_spei_bridge_readiness_20261013.json`;
- ignored detailed diagnostics and receipts:
  `data/interim/us_county/us_direct_practice_spei_bridge_readiness_v4_20261013*`.

# Historical Hultgren precipitation-basis climatology

## Result

The quantity-only EPA/FAIR benchmark now has a crop-calendar-specific
historical precipitation basis for rainfed and irrigated maize. Daily
GSWP3-W5E5 precipitation for 1981--2010 was accumulated to calendar months,
mapped to the fixed GGCMI maize calendars, transformed into the six published
Hultgren precipitation terms, and averaged over 29 complete harvest years
(1982--2010). This is an input milestone, not a crop response, damage, or SCC
estimate.

The output contains 48,889 regime-cell rows: 29,750 rainfed and 19,139
irrigated. These retain 95.402% and 99.169%, respectively, of positive MIRCA
maize area with a valid calendar after applying the preregistered four- to
ten-month season rule. The union contains 32,301 unique climate cells. All
10,957 daily time steps were read, with zero missing daily cell pairs. The
Parquet artifact is 2,459,600 bytes.

## Features and interpretation

For each cell-regime-calendar, the file records the long-run means of rainfall
in the planting month, months 2--4, and later crop-season months, plus the
corresponding sums of squared monthly rainfall in each phase. These are the
exact precipitation-only terms needed for proportional scaling in the
registered annual-quantity benchmark. They preserve each cell's fixed
historical within-season distribution while changing annual rainfall
quantity. They therefore do **not** capture climate-driven timing,
distribution, dry-spell, extreme-rainfall, or drought changes.

## Validation and resource bounds

The full build passed source hash, grid, units, daily chronology, complete
cell-month, finite-value, nonnegative-rainfall, unique-key, and output-size
checks. A separate implementation re-read all 10,957 daily source steps at
five fixed key-order rainfed/irrigated sentinels and independently rebuilt 145
crop-year bases. Maximum absolute discrepancies were zero for all linear
terms and at most `5.82e-11` for the squared terms. It also rechecked all raw,
calendar, area, output, and receipt identities.

The build's sampled peak process-group RSS was 354,074,624 bytes and the
independent validation's was 230,359,040 bytes, each below the 512 MiB worker
ceiling. The durable result artifact is below the 64 MiB owned-output limit.

## Artifacts

- Builder: `scripts/build_hultgren_precip_basis_climatology.py`
- Unit tests: `scripts/test_build_hultgren_precip_basis_climatology.py`
- Independent validator: `scripts/validate_hultgren_precip_basis_climatology.py`
- Build receipt: `data/provenance/hultgren_precip_basis_climatology_20260924.json`
- Validation receipt: `data/provenance/hultgren_precip_basis_climatology_validation_20260924.json`
- Ignored derived data: `data/interim/hultgren_precip_basis_climatology_20260924.parquet`

## Remaining gate

The next step is to combine this basis with the independently validated
cell-level annual-rainfall climatology, EPA country/model slopes, matched FAIR
baseline/pulse temperature paths, published Hultgren coefficients, and common-
price maize weights. A provisional partial SCC remains closed until the
zero/pre-pulse, support, tail, shrinking-pulse convergence, welfare, independent
reconstruction, and GIVE agriculture-replacement tests in the registered
protocol pass.

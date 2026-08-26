# Leakage-safe SPEI competitor design

Status: method and source decision locked on 2026-08-26; the fail-closed,
resumable bounded-construction pipeline, independent numerical tests, and the
two authorized one-cell engineering runs are complete, while full-grid
construction and outcome fitting remain gated.
The executable design gate is
`config/spei_competitor_v1.toml`, and the dated source record is
`data/provenance/spei_source_decision_20260826.toml`.

Validate the portable tracked contract with
`./.venv/bin/python scripts/validate_spei_competitor_contract.py`; add
`--require-local-inputs` to recheck that both ignored daily-weather roots are
present. Synthetic failure tests are in
`scripts/test_spei_competitor_contract.py`. Physical/time primitives and
tests are `scripts/spei_construction_primitives.py` and
`scripts/test_spei_construction_primitives.py`. The independent UBPWM/GLO
implementation, frozen monthly engine, bounded runner, and their tests are
`scripts/spei_distribution.py`, `scripts/spei_monthly_engine.py`,
`scripts/build_spei_grid_chunk.py`, and the corresponding `test_*.py` files.
The frozen CRAN SPEI 1.8.1 numerical behavior oracle is
`data/fixtures/spei_cran_1_8_1_synthetic_oracle.json`; it contains numerical
outputs only and no GPL implementation code.

## Decision

Compute the primary SPEI competitor from the daily weather already acquired
for each panel:

- U.S. counties: NOAA nClimGrid-Daily precipitation and mean/minimum/maximum
  temperature, 1981-2019.
- Global maize/soy: ISIMIP3a GSWP3-W5E5 v1.3 `pr`, `tas`, `tasmin`, and
  `tasmax`, 1981-2019.

This route keeps the drought index on the same weather realization and native
grid as the direct-precipitation competitor, needs no large source download,
and permits a calibration that ends before the common 2012 terminal holdout.
It is preferable to inserting a rolling published field whose later climate
has already influenced the standardization.

The published products remain useful, but only as independent retrospective
checks:

| Product reviewed on 2026-08-26 | Current source facts | Role here |
|---|---|---|
| NOAA/NIDIS nClimGrid-Monthly SPEI | Rolling 1895-present 5 km files; Pearson III and gamma; PET header says Thornthwaite; PET and SPEI headers say calibration 1895-2014; six 1/3/6-month candidates total 13.88 GB; U.S. federal-data license status with no product SPDX identifier | Excluded from the 2012 terminal score because its calibration overlaps 2012-2014; bounded retrospective implementation check only |
| SPEIbase v2.11 | Live CSIC page: CRU TS 4.09, 1901-2024, 0.5 degree, scales 1-48, FAO-56 Penman-Monteith, log-logistic, SPEI 1.8.1; ODbL 1.0 plus DbCL; selected 1/3/6 files total 1.15 GB | Excluded from terminal scoring because it is not source-consistent and its exact v2.11 calibration code is not public: the public repository still documents v2.10 and calls `SPEI::spei` without a reference subset, implying full-record fitting under the documented default |

The NOAA conclusion is verified from current NetCDF headers rather than only
the landing-page prose. The SPEIbase full-record-calibration statement is an
explicit inference, not a claimed v2.11 fact: the header lacks calibration
attributes and the public generation repository lags the live product. That
transparency gap is itself sufficient to keep the product out of a prospective
terminal comparison.

## Locked construction

The primary evaporative-demand term is daily Hargreaves-Samani reference ET0:

`ET0 = max(0, 0.0023 * 0.408 * Ra * (Tmean + 17.8) * sqrt(max(Tmax - Tmin, 0)))`

Here temperature is degrees Celsius, `Ra` is daily extraterrestrial radiation
in MJ m-2 day-1 calculated from grid-cell latitude and day of year using the
FAO-56 astronomical equations, `Tmean = (Tmin + Tmax) / 2`, and ET0 is mm
day-1. The source `tavg`/`tas` field remains the shared temperature-control
input but is not substituted for this Hargreaves mean. This is climatic
reference evaporative demand, not actual evapotranspiration, irrigation,
root-zone soil moisture, or crop water use. Hargreaves is selected because all
required inputs exist locally and consistently for both panels. FAO-56
Penman-Monteith is the preferred fuller-data sensitivity, but global radiation,
humidity, wind, and pressure drivers are not presently acquired for this task.
That sensitivity is nonblocking and must use the same weather source and
frozen calibration. Thornthwaite is not the primary PET formulation.

For every native grid cell:

1. Preserve source day labels. Convert global precipitation from kg m-2 s-1
   to mm day-1 and temperature from kelvin to Celsius; nClimGrid is already in
   mm and Celsius.
2. Sum complete daily precipitation and ET0 to calendar months and form
   `D = P - ET0`. Missing source days fail the cell-month; there is no
   climatological fill.
3. Form right-aligned rectangular 1-, 3-, and 6-month sums, including the
   current month. August-December 1981 supplies the five preceding months
   needed for the first calibrated SPEI-6 value in January 1982.
4. For each scale, grid cell, and calendar month separately, fit one
   three-parameter generalized-logistic distribution (the distribution named
   `log-Logistic` by SPEI 1.8.1) by unbiased probability-weighted
   moments on the 30 values from 1982-2011. Fit no crop outcome and use no
   2012-or-later climate.
5. Transform the fitted log-logistic CDF with the inverse standard-normal CDF,
   so negative values denote dry balance. Clip probabilities only at `1e-12`
   and `1 - 1e-12` to prevent numeric infinities, and audit every clipped
   value; clipping cannot be a model-selection rule.
6. Apply those parameters unchanged to all analysis months. A cell/calendar
   month with fewer than 30 finite calibration values or a degenerate fit
   fails; it is not imputed.

This follows the original multiscalar precipitation-minus-PET construction of
[Vicente-Serrano et al. (2010)](https://doi.org/10.1175/2009JCLI2909.1) and
the log-logistic unbiased-PWM guidance and PET sensitivity discussion in
[Begueria et al. (2014)](https://doi.org/10.1002/joc.3887). The selected ET0
formulation is from
[Hargreaves and Samani (1985)](https://doi.org/10.13031/2013.26773); the
astronomical calculations and Penman-Monteith sensitivity boundary follow
[FAO-56](https://www.fao.org/4/x0490e/x0490e00.htm).

The 1982-2011 climatology is outcome-blind and clean for a terminal 2012+
index transform. It is not a forecast-as-of-1982 transform: climate after the
1982-1989 early episode enters the standardization. Therefore the existing
global two-episode early-versus-later score must not be relabeled prospective.
The defensible global temporal diagnostic uses the continuous 1982-2016 panel
for development and reserves 2012-2016 for the terminal score. Spatial and
stress validation inside 1982-2011 remains a fixed-climatology retrospective
diagnostic.

The calibration starts in 1982 rather than using 1981-2010 because January-May
1981 six-month balances would require unavailable 1980 weather. The selected
window supplies 30 complete calendar-month samples at every scale and still
ends before the 2012 terminal block.

## Crop-calendar features and exact support

Standardize on the native grid before spatial or crop-area aggregation. In the
U.S. route, apply the existing fixed county-polygon nClimGrid weights to each
monthly SPEI field, then use the locked 2010 NASS usual-date calendar. In the
global route, calculate stage features separately under the existing GGCMI
`noirr` and `firr` calendars, then apply the same fixed, outcome-independent
MIRCA-OS v2 regime weights used by the direct/scPDSI candidates. Do not
standardize an already aggregated county or irrigation mixture.

The local 1981 weather start was checked against the actual global calendars,
positive MIRCA shares, and current 1982-1989 common support. For SPEI-6, an
illustrative pre-construction audit finds 16 maize 1982 common-support cells
(15 with observed yield) that need late-1980 balance months even for the season
window, and no soybean primary cells. The locked rule is algorithmic, not the
count: for every window and scale, derive the earliest required balance month;
if it precedes the source start, remove that key from every family through the
master intersection without partial filling or irrigation-weight
renormalization. Generate and hash a new coverage receipt on the continuous
panel before construction. The preplant-90 audit finds a larger illustrative
1982 boundary (444 maize and 29 soybean common rows, of which 82 and 9 have
observed yield), so its global comparison starts in 1983. Preserving those
1982 keys would require a separately reviewed pre-1981 GSWP3-W5E5 acquisition.

The primary feature is the day-weighted crop-season mean for one SPEI scale.
Preplant-90 and three stage means are predeclared secondary specifications.
Monthly minima and day-equivalents at or below -1 and -1.5 are descriptive
extensions, not daily observations: a monthly index is held constant only to
weight its exact overlap with a crop-calendar window. The 1-, 3-, and 6-month
scales are reported as separate models; they are neither selected by outcomes
nor stacked.

Overlap weighting is a retrospective crop-season approximation, not an
operational within-season forecast. A monthly SPEI value contains the complete
month's weather, so a partial planting or maturity boundary can contain days
outside the exact crop window even though only overlapping days receive
weight. Disclose this explicitly. A prespecified timing sensitivity uses only
SPEI observations whose month-end timestamp falls inside the window; it avoids
post-window weather but omits partial boundary-month exposure. Apply the same
alignment rule to PDSI/scPDSI and SPEI within any comparison.

Before any fit, construct one master inner intersection across direct
precipitation, PDSI/scPDSI, SPEI-1, SPEI-3, and SPEI-6. Require exact equality
of:

- U.S. level keys: county, crop, harvest year, and irrigation practice;
- global post-allocation level keys: harvest year, latitude, longitude, and
  crop;
- outcomes and observed/missing flags;
- calendar, polygon/crop-area, and irrigation-weight lineage;
- shared temperature/heat controls; and
- spatial, temporal, and stress split labels and test-key hashes.

Common support does not erase calibration differences. U.S. NOAA PDSI ends its
publisher calibration in 1990 and is eligible for the 2012 terminal comparison.
The current global CRU scPDSI field self-calibrates over 1901-2025, so its score
remains retrospective context even on identical rows; it cannot promote or
displace a model using the terminal score. The leakage-safe global terminal
ranking is direct precipitation versus the separately reported SPEI-1/3/6
models. This does not authorize choosing a SPEI scale on terminal outcomes.

Form first differences only between consecutive years within the level key.
Purge from training any pair that shares an endpoint with a test pair, and
never bridge 1989 to 2012. Audit support lost by family, scale, crop, year, and
irrigation stratum. Family-specific imputation is prohibited.

Every outcome model may contain zero or one moisture family: direct
precipitation, PDSI/scPDSI, or one SPEI scale. The identical temperature and
heat controls may appear in every model, but raw precipitation, raw PET,
PDSI/scPDSI, or a second SPEI scale cannot enter a SPEI model. Family effects
cannot be added, summed, or interpreted as separate damages.

## Bounded engineering execution

The two authorized one-cell runs completed on 2026-08-26 under algorithm
identity `spei_grid_chunk_v2_environment_bound` and numerical-environment
identity SHA-512
`9c8d50f500c873097f433413be1979d1c3e82c0720e7840beca28f2a9d6d92cfd212e9fb0d828c5b2b4b50f31516c5d043b5b376f0b7502039a4ff6c0201e0a1`.
Both exact reruns returned `resumed_complete` after revalidating every source
object and the durable artifact. The machine-readable validation record is
`data/provenance/spei_bounded_chunks_20260826.json`.

| Source | Exact one-cell support | Runtime and peak RSS | Output and fit audit |
|---|---|---|---|
| nClimGrid-Daily | grid slice `[370:371, 592:593]`, 39.9791679382 N, 100.0208358765 W; 468 complete cell-months | 173.446 s; 450,854,912 bytes (429.97 MiB) | 118,556-byte NetCDF; 36/36 valid fits; one audited lower-tail clip at scale 6 and no other clips |
| ISIMIP3a GSWP3-W5E5 | grid slice `[100:101, 160:161]`, 39.75 N, 99.75 W; 468 complete cell-months | 98.244 s; 217,268,224 bytes (207.20 MiB) | 119,458-byte NetCDF; 36/36 valid fits; no tail clips |

An independent post-run audit verified all 84 JSON receipt envelopes, all 78
annual checkpoint file digests and environment identities, both final NetCDF
digests, coordinates, chronology, scale support, water-balance identities,
fit/missingness codes, and closed scientific-use gates. No outcome row was
read, no imputation occurred, and neither run was a full-grid execution.

Earlier attempts created before numerical-library and platform versions were
bound into the run/checkpoint identity are preserved under
`outputs/spei_competitor_v1/superseded_pre_environment_bound_chunks_20260826`.
They are quarantined, superseded, and explicitly excluded from evidence and
reporting; only `outputs/spei_competitor_v1/env_bound_chunks_v1` is valid for
this bounded engineering check.

## Implementation roadmap and gates

1. Completed: calendar-month GLO UBPWM fitting, frozen-parameter application,
   observation-level tail-clip auditing, missingness/degeneracy failures, and
   synthetic comparison to an independently executed CRAN SPEI 1.8.1 stack.
2. Completed for the two authorized one-cell chunks: annual resumable source
   checkpoints, full SHA-512 source revalidation, numerical-environment
   binding in run/checkpoint identities, source/contract/output receipts, and
   native-grid NetCDF output. Each invocation remains capped at 64 cells and
   cannot fit outcomes or run a full grid. No additional chunk execution is
   authorized by this result.
3. Build versioned monthly grid fields and receipts; then create county and
   crop-calendar features with source, PET, scale, calibration, grid, and
   weight metadata on every output.
4. Extend the existing separate-family common-support builders to SPEI-1/3/6
   and require one shared support/split receipt across every reported model.
5. Seek separate authorization before fitting outcomes. No code or artifact
   from this design authorizes coefficient export, causal interpretation,
   damages, projections, or SCC use.

No user decision is required to begin this primary route. A later decision to
preserve the excluded 1982 global keys or fund the larger FAO-56
Penman-Monteith input acquisition would add source coverage or a
prespecified PET sensitivity; it does not block Hargreaves implementation and
must not be chosen by predictive, damage, or SCC magnitude.

## Authoritative data and software sources

- NOAA NCEI, [nClimGrid-Daily and DOI](https://doi.org/10.25921/c4gt-r169).
- NOAA/NIDIS, [nClimGrid-Monthly index README](https://www.ncei.noaa.gov/pub/data/nidis/indices/nclimgrid-monthly/nidis_nclimgrid_readme_c20220520.txt) and [SPEI product page](https://www.drought.gov/data-maps-tools/us-gridded-standardized-precipitation-index-spei-nclimgrid-monthly).
- ISIMIP, [GSWP3-W5E5 description](https://www.isimip.org/gettingstarted/input-data-bias-adjustment/details/110/) and [v1.3 DOI](https://doi.org/10.48364/ISIMIP.982724.3).
- CSIC, [SPEIbase current database page](https://spei.csic.es/database.html) and [public generation repository](https://github.com/sbegueria/SPEIbase).
- Begueria, Vicente-Serrano, and Angulo-Martinez (2010), [SPEIbase primary description](https://doi.org/10.1175/2010BAMS2988.1).
- CRAN, [SPEI 1.8.1 package](https://cran.r-project.org/package=SPEI).

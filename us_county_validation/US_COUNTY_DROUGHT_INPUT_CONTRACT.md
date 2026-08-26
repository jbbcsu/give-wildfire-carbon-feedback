# U.S. county PDSI/SPEI competing-family input contract

## What this implements

This track tests whether a climatic drought index predicts U.S. county crop
outcomes more reliably than the direct precipitation/temperature feature
family. It does not assume that a drought index is superior. All comparisons
must use the same outer spatial, temporal, and extreme holdout outcome rows,
and a null or worse drought result remains a result.

Within the direct-weather family, the parsimonious precipitation-quantity
specification is the baseline. Within-season timing/distribution features are
retained only if they add robust outer-holdout value; they are not privileged
by the research framing.

The moisture families are mutually exclusive in an estimation run:

1. direct precipitation and temperature features;
2. PDSI; or
3. one declared SPEI scale/distribution candidate.

PDSI and SPEI embed precipitation and evaporative demand. They therefore are
not appended to the direct weather matrix and their estimated impacts are not
summed with direct precipitation/temperature impacts. A future joint
decomposition would require a separate, frozen counterfactual design.

## Real PDSI source now available

NOAA NCEI's exact dated county object
`climdiv-pdsicy-v1.0.0-20260806` is acquired under the gitignored raw-data
tree. Its byte length (40,602,276), SHA-512, ETag, Last-Modified value, fixed
record structure, and NOAA documentation are recorded in
`data/provenance/nclimdiv_county_pdsi_20260806.toml`.

The object has 410,124 fixed-width records: 3,107 internal county keys by 132
years (1895--2026). Every record has element code `05` and twelve monthly
fields. The 15,535 missing values are exactly August--December 2026. No
requested 1981--2019 value is missing.

The first two key digits are **not Census state FIPS**. They follow NOAA's
alphabetical internal state-code table, while NOAA documents the next three as
the within-state county code. For example, NOAA internal key `25039` is Cuming
County, Nebraska (Census GEOID `31039`). Treating `25039` as a Census GEOID
would silently assign the Nebraska series to Massachusetts. The extractor
therefore uses an explicit official-state-table-to-Census crosswalk and the
test suite locks the Cuming County 2012 values against NOAA's county API.

An all-key comparison against the acquired 2019 TIGER/Line county inventory
finds 3,106 exact matches among 3,107 keys. Transformed NOAA key `24511` is
absent from TIGER, while TIGER key `51678` is absent from NOAA. Their causes
are not guessed. The implemented full-panel route resolves this conservatively:
it extracts only the 799 direct-practice counties that already passed the
separate historical-geography gate, so neither unmatched key can enter the
estimation input. The pinned bulk file then supplies 383,520 complete monthly
PDSI rows for those counties over 1980--2019. This support restriction is not
an inferred crosswalk and does not establish national representativeness.

NOAA states that its PDSI uses a 1931--1990 calibration and does not include
man-made changes. Consequently, this is a meteorological water-balance index,
not observed irrigation, soil moisture, or water applied. It can be evaluated
separately in high-rainfed and mixed/irrigated samples, but a coefficient
difference is not automatically an identified irrigation-adaptation effect.

A bounded real execution first extracted all 480 Cuming County months from
1980--2019 and constructed 20 crop-calendar windows for 1981 corn and soybean
under the fixed-primary and broad-window calendars. All twelve 1981 bulk
values independently match NOAA's county API. The derived file identities and
checksums are recorded in
`data/provenance/nclimdiv_county_pdsi_cuming_smoke.toml`. That smoke establishes
the source-key and calendar machinery only. The subsequent locked corn/soy
join contains 118,610 crop-calendar index-window rows on the same 23,722
practice-specific level outcomes used by the direct-weather diagnostic; its
source receipt is
`outputs/us_county/competing_moisture_predictive_v1/pdsi_source_validation.json`.
Neither construction is itself a crop-yield relationship.

## SPEI route and calibration resolution

NOAA/NIDIS publishes nClimGrid-Monthly SPEI at approximately 5 km for 1-, 3-,
and 6-month (among other) scales, with gamma and Pearson Type III fitting and
a published 1895--2014 base period. Current PET and three-month NetCDF headers
were checked and confirm the 1895--2014 calibration; the PET header identifies
Thornthwaite. The exact current HTTP identities for the six 1/3/6-month files
are pinned in
`data/provenance/nclimgrid_monthly_spei_candidates.toml`.

Those six objects total 13,878,714,816 bytes and were not downloaded. More
importantly, their calibration includes 2012--2014 climate from the terminal
holdout in `us_competing_moisture_predictive_v1.toml`. The published field is
therefore ineligible for that terminal comparison regardless of storage. It
may remain a bounded retrospective implementation check; the Pearson/gamma
ordering below is legacy metadata for that check, not a primary predictive
choice.

The original SPEI formulation is based on accumulated precipitation minus
potential evapotranspiration and a fitted probability distribution. The new
primary design in `config/spei_competitor_v1.toml` instead computes
source-consistent SPEI from the already acquired nClimGrid-Daily precipitation
and temperature, using daily Hargreaves-Samani reference ET0, 1/3/6-month
accumulations, a log-logistic unbiased-PWM fit by grid cell and calendar month,
and a frozen 1982--2011 calibration. See `SPEI_COMPETITOR_DESIGN.md`. This is a
historical predictive competitor only; it does not authorize a future forcing,
damage calculation, or SCC use.

## Crop-calendar features

Each monthly index is day-weighted over the exact overlap with:

* the 90 days before planting;
* stages defined by the frozen `0/0.3/0.7/1` engineering fractions; and
* the full crop season.

The builder records the window mean, minimum, and day-equivalent counts below
family-specific moderate/severe thresholds. “Day-equivalent” means a monthly
index value is held constant only for weighting the days of that calendar
month; it is not a claim that daily PDSI/SPEI was observed. Missing months fail
the whole eligible window. This overlap rule is retrospective and does not make
the exposure daily-exact: a monthly value contains the complete month's
weather, including days outside a partial planting or maturity boundary. A
month-end-only timing sensitivity under the replacement contract avoids
post-window weather at the cost of omitting partial boundary-month exposure;
PDSI and SPEI must use the same rule within a comparison. The primary and broad
NASS-calendar roles stay separate.

## Leakage and common-holdout gates

The NOAA PDSI 1931--1990 and published NOAA SPEI 1895--2014 calibration windows
are fixed independently of crop outcomes, but only PDSI ends before the 2012
terminal holdout. The published SPEI path must fail that gate. The replacement
SPEI calibration is outcome-blind 1982--2011 and is applied unchanged to the
2012+ climate. Every model-family comparison must inner-join direct weather,
PDSI, and each reported SPEI scale to the same outcome keys and preserve the
same spatial, temporal, and extreme split labels. No yield or holdout statistic
may enter index construction or scale choice.

The executable lock for the existing PDSI and published-NOAA benchmark path is
`config/us_county_drought_predictor_contract_v1.toml`. The replacement primary
method lock is `config/spei_competitor_v1.toml`. All current outputs remain
historical validation inputs with response estimation, damages, and SCC use
set to false.

`validate_competing_moisture_family_support.py` provides the last pre-fit
gate for PDSI and the legacy published-NOAA Pearson/gamma schema. It is not yet
a computed-Hargreaves/log-logistic SPEI gate; extending it under the new
contract is an explicit implementation prerequisite. For its supported inputs,
it requires one unique direct-weather row and one unique row from each
candidate drought family for exactly the same county/crop/year/practice keys,
preserves a single common spatial/temporal/extreme fold table, keeps each
county in one spatial fold, and requires the temporal holdout to be a terminal
block. It rejects raw weather and outcome columns inside PDSI/SPEI matrices,
checks the publisher-fixed source/calibration plus the locked SPEI
scale/distribution, and requires calibration to end before the final temporal
holdout. It writes only a support audit; it does not fit or rank a model.

## Global robustness boundary

The existing CRU scPDSI machinery remains a global historical benchmark.
NOAA county PDSI and NOAA/NIDIS SPEI remain U.S. products. The global SPEI
competitor now has a source-consistent historical design using the already
acquired ISIMIP3a GSWP3-W5E5 precipitation and daily temperatures, the same
Hargreaves/log-logistic method and 1982--2011 calibration, and the existing
GGCMI/MIRCA calendar-allocation lineage. It remains a predictive diagnostic
only. PDSI/scPDSI or one SPEI scale replaces, rather than adds to, direct
precipitation for the moisture family.

## Reproduction commands

From the isolated `precipitation_scc` environment:

```bash
./.venv/bin/python us_county_validation/scripts/download_nclimdiv_county_pdsi.py

./.venv/bin/python us_county_validation/scripts/extract_nclimdiv_county_pdsi.py \
  --year-start 1980 --year-end 2019 \
  --county-inventory config/us_county_pdsi_geography_smoke.csv --county-geoid 31039 \
  --out data/interim/us_county/nclimdiv_pdsi_cuming_1980_2019.parquet

./.venv/bin/python us_county_validation/scripts/build_county_crop_calendar_drought_features.py \
  --monthly-index data/interim/us_county/nclimdiv_pdsi_cuming_1980_2019.parquet \
  --calendar config/us_county_ne_1981_calendar_smoke.csv --family pdsi \
  --out data/interim/us_county/nclimdiv_pdsi_cuming_1981_crop_calendar_smoke.parquet

./.venv/bin/python us_county_validation/scripts/audit_nclimdiv_tiger_geography.py \
  --nclimdiv data/raw/us_county/nclimdiv_pdsicy/climdiv-pdsicy-v1.0.0-20260806 \
  --tiger-shapefile data/raw/us_county/tigerline/tl_2019_us_county/tl_2019_us_county.shp \
  --out data/interim/us_county/nclimdiv_pdsi_tiger2019_geography_audit.json

./.venv/bin/python us_county_validation/scripts/test_us_county_drought_inputs.py
./.venv/bin/python scripts/verify_provenance.py data/provenance
```

The raw and interim outputs are ignored by Git. The tracked provenance records
pin every acquired or derived file used by this smoke.

## Authoritative and primary sources

* NOAA NCEI, [nClimDiv dataset and DOI](https://doi.org/10.7289/V5M32STR).
* NOAA/NIDIS, [nClimGrid-Monthly SPEI product](https://www.drought.gov/data-maps-tools/us-gridded-standardized-precipitation-index-spei-nclimgrid-monthly).
* Vose et al. (2014), [nClimDiv construction](https://doi.org/10.1175/JAMC-D-13-0248.1).
* Vicente-Serrano, Begueria, and Lopez-Moreno (2010), [SPEI method](https://doi.org/10.1175/2009JCLI2909.1).

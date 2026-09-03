# NASS irrigation-practice coverage screen

## Question and decision

Can the U.S. county validation estimate precipitation effects separately for
irrigated and non-irrigated crops, or must irrigation be handled only through a
county sample-selection proxy?

The answer is **both, for different estimands**. Official Quick Stats contains
long paired `IRRIGATED` and `NON-IRRIGATED` county-yield series for corn,
soybeans, and all-classes wheat. Those records support a regional
practice-specific validation design. They are not a national panel: the
geographic support is concentrated in states that historically published the
practice split, and recent paired support is thin. For the national
all-production-practices outcome, the defensible fallback is a crop-specific
Census of Agriculture share:

`irrigated harvested acres / total harvested acres`.

That share is a sample-selection or interaction variable, not a separate yield
outcome and not proof of annual irrigation status.

## Exact API screen

All requests use the official NASS Quick Stats count and data endpoints. The
key is read only from the Git-ignored `.secrets/nass.env`. The six yield
queries hold the following dimensions fixed and deliberately omit a year
filter so the response reveals the complete published time support:

| Dimension | Value |
|---|---|
| source / sector | `SURVEY` / `CROPS` |
| statistic / geography / frequency | `YIELD` / `COUNTY` / `ANNUAL` |
| reference period / domain | `YEAR` / `TOTAL` |
| class | `ALL CLASSES` |
| production practice | separately `IRRIGATED` and `NON-IRRIGATED` |
| crop utilization | corn `GRAIN`; soybean and wheat `ALL UTILIZATION PRACTICES` |
| unit | `BU / ACRE` |

Each query was preflight-counted and remained below the API's 50,000-row data
limit after the wheat class was locked. Raw JSON and credential-free manifests
remain ignored; exact local checksums are pinned in
`data/provenance/nass_irrigation_practice_screen.toml`.

### Direct practice-specific yield support

Positive numeric yields were required on both sides of a crop--county--year
pair. Numeric zero yields are retained in the audit as invalid observations
but excluded from usable support; no suppression value is converted to zero.

| Crop | API rows: irrigated / non-irrigated | Usable paired county-years | Paired counties | States | Paired years | Pairs in 1981--2019 | Pairs in 2018--2022 |
|---|---:|---:|---:|---:|---|---:|---:|
| Corn | 16,635 / 14,752 | 11,483 | 437 | 11 | 1944--2025 | 7,079 | 71 |
| Soybeans | 7,467 / 8,247 | 6,294 | 256 | 5 | 1960--2025 | 4,845 | 33 |
| Wheat, all classes | 22,001 / 35,112 | 18,831 | 703 | 14 | 1929--2007 | 9,672 | 0 |

Within the daily gridMET era and the working 1981--2019 historical-climate
window, paired support spans 366 counties in 10 states for corn, 255 counties
in five states for soybeans, and 639 counties in 14 states for wheat. This is
large enough to justify a **regional direct-practice validation track**, but
not to claim a nationally representative irrigation-specific response.
In particular, all-classes wheat has no paired observations after 2007, and
the recent corn/soybean pairs cover only a small fraction of national counties.

The executable full-window builder retains 43,192 long practice rows: 21,596
exact crop--county--year pairs. All 807 unique GEOIDs match the 2019 TIGER
county file. A conservative screen against official Census 1980s--2010s
county-change pages flags eight counties for explicit historical-boundary
resolution and two additional name/code-only reviews. The screen leaves 799
fixed-2019 proxy candidates; it does not assert that unflagged counties had no
minor boundary changes. Wheat remains blocked from weather construction until
class-specific winter, spring, and durum bases or weights exist.

## Census harvested-area fallback

The 2012, 2017, and 2022 Census queries fix crop, `ALL CLASSES`, `AREA
HARVESTED`, `COUNTY`, `ANNUAL`, `YEAR`, and `ACRES`, leaving production
practice open only during discovery. Each response contains exactly the two
needed series: `ALL PRODUCTION PRACTICES` and `IRRIGATED`. The 2022 report-form
guide defines irrigated harvested acres as harvested crop acres to which water
was applied by artificial or controlled means. NASS also states that `(D)` is
withheld to avoid disclosure. The audit therefore requires numeric numerator
and denominator values; a missing or suppressed irrigated record is not
treated as zero.

| Census year | Crop | Numeric share counties | States | Share <=10% | <=20% | <=30% | Numeric total but no usable irrigated numerator |
|---:|---|---:|---:|---:|---:|---:|---:|
| 2012 | Corn | 1,121 | 43 | 496 | 615 | 668 | 1,233 |
| 2012 | Soybeans | 720 | 30 | 435 | 505 | 547 | 1,158 |
| 2012 | Wheat | 612 | 38 | 323 | 414 | 470 | 1,533 |
| 2017 | Corn | 1,014 | 44 | 428 | 540 | 610 | 1,322 |
| 2017 | Soybeans | 706 | 33 | 393 | 472 | 511 | 1,207 |
| 2017 | Wheat | 420 | 36 | 219 | 271 | 304 | 1,482 |
| 2022 | Corn | 1,071 | 44 | 484 | 599 | 676 | 1,251 |
| 2022 | Soybeans | 785 | 32 | 480 | 560 | 598 | 1,093 |
| 2022 | Wheat | 485 | 37 | 245 | 311 | 362 | 1,445 |

The pre-outcome 2017 share is the recommended primary selector for the already
acquired 2018--2022 aggregate-yield panel. The 2012 and 2022 vintages are
required temporal sensitivities. Threshold counts above are diagnostics, not
a silently chosen primary threshold; 10%, 20%, and 30% must all be reported.

An outcome-free, post-acquisition stability audit intersects counties with a
numeric share in all three vintages. At the 10% selector, 2017--2022 agreement
is 92.28% for corn (751 common counties), 92.64% for soybeans (516), and
84.16% for wheat (303); the corresponding share correlations are 0.938,
0.954, and 0.834. The weaker wheat stability makes Census vintage a material
wheat sensitivity. These are descriptive selector diagnostics, not irrigation
effects, and they do not alter the primary 2017 selector or authorize a
response, damage function, or SCC input. Reproduce them with
`audit_irrigation_share_vintage_stability.py`; the tracked result is
`data/provenance/us_irrigation_share_vintage_stability_20260903.json`.

A counts-only audit next applies the fixed 2017 selectors to the locked
1981--2019 national all-practice panel without reading yield magnitudes. The
10/20/30% thresholds retain 15,772/19,832/22,219 reported corn county-years
(20.80%/26.15%/29.30% of the national panel) and
14,652/17,328/18,685 soybean county-years (23.65%/27.97%/30.16%). At 10%,
annual retained support ranges from 296 to 424 corn counties and 283 to 391
soybean counties. The large, threshold-sensitive coverage loss must be carried
into national response validation; it is not evidence of an irrigation effect
and does not authorize response, damage, or SCC use.

## Reproducible commands and fail-closed rules

Acquire the all-years practice-specific yield records:

    .venv/bin/python us_county_validation/scripts/download_nass_irrigation_practice_screen.py --mode yield-practice

Acquire a Census vintage (repeat for 2012, 2017, and 2022):

    .venv/bin/python us_county_validation/scripts/download_nass_irrigation_practice_screen.py --mode census-area-discovery --census-year 2017

Run the audit with the six exact yield files and the three crop files for one
Census year:

    .venv/bin/python us_county_validation/scripts/audit_nass_irrigation_practice_coverage.py --yield-input YIELD_JSON --area-input AREA_JSON --shares-out SHARES.csv --audit-out AUDIT.json

The audit fails on mixed series, non-county dimensions, non-`ALL CLASSES`
records, duplicate crop--county--year--practice keys, negative acreage, or an
irrigated share above one beyond a small rounding tolerance. It emits an
explicit exclusion reason when the denominator or numerator is unavailable.
Raw and derived files remain under ignored `data/raw/` and `data/interim/`.

Build and geography-screen the complete 1981--2019 direct-practice support:

    .venv/bin/python us_county_validation/scripts/build_nass_direct_practice_panel.py [six locked yield paths] --out PANEL.parquet --audit-out PANEL.audit.json
    .venv/bin/python us_county_validation/scripts/audit_nass_direct_practice_geography.py --panel PANEL.parquet --tiger-counties TIGER.shp --change-1980 1980.html --change-1990 1990.html --change-2000 2000.html --change-2010 2010.html --out GATE.csv --audit-out GATE.audit.json

Both commands explicitly leave response and SCC authorization false.

Audit the fixed selector across Census vintages:

    .venv/bin/python us_county_validation/scripts/audit_irrigation_share_vintage_stability.py --shares-2012 data/interim/us_county/nass_2012_crop_irrigation_shares.csv --shares-2017 data/interim/us_county/nass_2017_crop_irrigation_shares.csv --shares-2022 data/interim/us_county/nass_2022_crop_irrigation_shares.csv --out data/provenance/us_irrigation_share_vintage_stability_20260903.json

Audit counts-only selector retention in the national panel:

    .venv/bin/python us_county_validation/scripts/audit_national_irrigation_selector_support.py --panel data/interim/us_county/nass_national_all_practice_panel_1981_2019.parquet --out data/provenance/us_national_irrigation_selector_support_20260903.json

## Next empirical use

1. Estimate a regional paired-practice specification with separate weather
   responses or weather-by-practice interactions, using only counties and
   years in the common support and validating against an aggregate-yield
   specification for the same support.
2. For the national all-practice panel, use 2017 crop-specific shares for the
   primary high-rainfed selection; report 2012/2022 share vintages and 10/20/30
   percent thresholds as sensitivity checks.
3. Do not infer that counties without a published irrigated-acre numerator are
   rainfed. Exclude them from the strict share-gated sample and report the
   resulting coverage loss.
4. Do not transfer regional U.S. practice coefficients to unsupported global
   regions or add the U.S. estimate as a second SCC damage term.

Authoritative sources: USDA NASS [Quick Stats](https://www.nass.usda.gov/quick_stats/),
[developer/API documentation](https://www.nass.usda.gov/developer/), the
[2022 Census report-form guide](https://data.nass.usda.gov/AgCensus/Report_Form_and_Instructions/2022_Report_Form/2022_Census_of_Agriculture_Report_Form_Guide.pdf),
and the [2022 Census confidentiality FAQ](https://www.nass.usda.gov/AgCensus/FAQ/2022/).

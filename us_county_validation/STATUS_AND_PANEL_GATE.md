# County validation: executable status and gates

## Observed local input state (audited 2026-08-26)

| Input | Local state | Permitted conclusion |
|---|---|---|
| NASS Quick Stats crops snapshot dated 2026-08-21 | Pinned identity sidecar exists; resumable partial is 104 MiB of expected 1,128,988,003 bytes; archive is incomplete | Do not inspect/filter as if valid gzip; no NASS yield observation has entered a panel |
| NASS Quick Stats API | Locked 2019--2021 corn-grain queries passed; exact-series preparation retained 4,396 real-FIPS county-years and separately counted 254 combined/non-FIPS records | Real national/county outcome acquisition only; observations aggregate all production practices and have not entered a weather-response panel |
| U.S. Drought Monitor county area shares | Real Iowa 2001 raw response and prepared county-week table exist | A real source/provenance check only; no documented crop-season calendar or NASS outcome overlap exists |
| gridMET / Daymet daily climate | No raw files or derived county crop-area features found | No timing, dry-spell, temperature, or heavy-rain county exposure can be estimated |
| Crop-area masks/weights | Not found | County-centroid weather is not substituted as the main exposure |
| Crop-specific irrigated/non-irrigated harvested area | Not found | No county is called non-irrigated or high-rainfed; no irrigation gate can pass |

There is therefore **no real county yield-response result** and no valid
non-irrigated county panel as of this audit, although the API outcome path is
now operational.

## New reproducible NASS path

After archive completion, use the streaming extractor rather than an ad hoc manual export:

    python us_county_validation/scripts/extract_nass_bulk_county_yields.py \
      --input data/raw/us_county/nass/qs.crops_20260821.txt.gz \
      --commodity CORN --year-min 1981 --year-max 2024 \
      --out data/interim/us_county/nass_corn_total_1981_2024.parquet

It scans gzip-compressed tab-separated Quick Stats data in chunks, applies explicit total/all-practice/annual county-yield filters, preserves NASS suppression flags, rejects duplicate county-years or mixed units, and retains exact series descriptors. The defaults are a documented starting series—not a claim that it is irrigation-specific. Run the synthetic invariant check:

    python us_county_validation/scripts/test_extract_nass_bulk_county_yields.py

## Burke-style panel gate

The first estimable design is a crop-specific county-by-harvest-year panel:

    log(y_c,t) = county FE + year FE + f(T stage, P total, P distribution, CDD, heavy rain) + error.

It needs, in this order:

1. A completed/verified NASS archive and one explicitly selected yield series.
2. Crop-specific irrigated-area shares to set a preregistered high-rainfed selection threshold; generic NASS yield remains aggregate.
3. Crop-area-weighted daily gridMET exposures, calendar-aligned into planting, vegetative, reproductive, and grain-fill windows. Daymet is a robustness product, not a primary substitute.
4. Complete state/crop/year calendar rows and USDM county-week records for the same county-years, enabling the fixed-effect composite-drought benchmark.
5. Predeclared rolling-year, spatial/state, and dry/wet-extreme holdouts before choosing among total-only, seasonal-shape, dry/wet-extreme, binned, and constrained-nonlinear specifications.

No API key is needed for the pinned NASS bulk-archive route. The 2026-08-25
resume attempt failed at remote HTTP header/range transfer (curl exit 56), an
upstream/transport condition. The owner subsequently authorized the Quick
Stats API fallback and supplied a local Git-ignored key. The fallback is now
count-first, one commodity-year per request, exact-series filtered, and
provenance/checksum recorded; the key is never written to output. The dated
bulk release remains the replication benchmark if its transfer completes.

## Climate/drought interpretation constraint

USDM is an observed composite-drought validation benchmark only. It cannot be projected or added to direct precipitation-pattern effects. Direct daily climate features and USDM/PDSI/SPEI are competing exposure families, not blindly stacked in one regression. This county module validates response shape/heterogeneity and never creates a separate US SCC term.

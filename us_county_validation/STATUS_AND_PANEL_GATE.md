# County validation: executable status and gates

## Observed local input state (audited 2026-08-26)

| Input | Local state | Permitted conclusion |
|---|---|---|
| NASS Quick Stats crops snapshot dated 2026-08-21 | Pinned identity sidecar exists; resumable partial is 104 MiB of expected 1,128,988,003 bytes; archive is incomplete | Do not inspect/filter as if valid gzip; no NASS yield observation has entered a panel |
| NASS Quick Stats API | Locked 2018--2022 all-practice corn retained 7,253 real-FIPS county-years. The complete 1981--2019 direct-practice builder retains 7,079 corn, 4,845 soybean, and 9,672 all-classes-wheat paired county-years (43,192 long rows), but only regional support. | Direct practice records can support regional validation; they are not a nationally representative panel and have not entered a weather-response estimate |
| U.S. Drought Monitor county area shares | Real Iowa 2001 raw response and prepared county-week table exist | A real source/provenance check only; no documented crop-season calendar or NASS outcome overlap exists |
| nClimGrid / gridMET / Daymet daily climate | January and May--October 1981 NOAA nClimGrid four-variable files are pinned; a real 184-day Cuming corn/soy feature smoke exists. A complete HEAD inventory pins all 468 monthly 1981--2019 identities and 27,857,685,556 aggregate bytes, but the remaining NetCDF bodies are not acquired. One gridMET 2018 precipitation file is pinned; no Daymet object is acquired. | nClimGrid is primary and gridMET/Daymet are robustness routes. HTTP metadata is not file provenance; each acquired month still needs local hash, schema, and date checks. The Cuming features validate construction only; they are not a climate--yield result. |
| Spatial weights and crop masks | 2019 TIGER is acquired and produced 120 exact county/nClimGrid polygon intersections for Cuming. The exact 2017 national CDL is acquired; 706,394 corn and 582,110 soybean pixels in Cuming map to 120 cells per crop. | County-polygon area weighting is the full-period primary county-average proxy. Fixed-2017 CDL crop pixels are a separate sensitivity; their use for 1981 is explicitly retrospective. |
| Crop calendars | Exact NASS 2010 usual-date PDF acquired, checksummed, and visually audited. A tested parser preserves 130 source state/crop rows and expands 10,920 unique 1981--2022 primary/broad calendar rows across 42 states and five crop classes; all pass the executable calendar gate. | Floor midpoint of most-active ranges is the engineering default and the begin-to-end envelope is a sensitivity. These are fixed usual dates, not annual phenology. All-classes wheat still requires class-specific bases/shares. |
| Crop-specific irrigated/non-irrigated harvested area | Exact 2012, 2017, and 2022 Census `IRRIGATED` and `ALL PRODUCTION PRACTICES` harvested-acre series acquired for corn, soybean, and all-classes wheat. The 2017 audit retains numeric shares for 1,014, 706, and 420 counties, respectively. | The 2017 share is eligible as a fixed pre-outcome selector; 2012/2022 are sensitivities. Missing/suppressed numerators remain excluded, never zero-filled |
| Historical county geography | All 807 direct-practice GEOIDs match 2019 TIGER. Official Census decade pages conservatively flag eight geometry-change-review counties and two name/code-only counties; 799 remain fixed-2019 proxy candidates after this screen. | Page absence does not prove absence of minor changes. Flagged geometry cases need exclusion or historical-boundary sensitivity before weather construction. |

There is therefore **no real county yield-response result** as of this audit.
A four-row, one-county weather/outcome construction smoke exists for paired
irrigated/non-irrigated corn and soybean support, under both the primary county-
polygon proxy and a retrospective 2017 CDL sensitivity. It is too small and
was not authorized for response estimation. Full historical climate download,
multi-county weather aggregation, explicit resolution of the eight boundary-
screen cases, and predeclared estimation/validation are the binding empirical
inputs. Exact practice support and Census-share
coverage are recorded in
[NASS_IRRIGATION_PRACTICE_SCREEN.md](NASS_IRRIGATION_PRACTICE_SCREEN.md).

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
2. Join the audited 2017 crop-specific irrigated-area shares to set a preregistered high-rainfed threshold; report 2012/2022 vintages and 10/20/30 percent thresholds. Generic NASS yield remains aggregate. A separate regional direct-practice panel is a validation track, not a national replacement.
3. County-polygon area-weighted daily nClimGrid exposures as the full-period
   primary county-average proxy, plus fixed-CDL crop-pixel sensitivities where
   their vintage is defensible. Build nonlinear bases at weather-cell/calendar-
   class level before either spatial route and before wheat-class weighting.
   gridMET and Daymet are weather-product robustness routes.
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

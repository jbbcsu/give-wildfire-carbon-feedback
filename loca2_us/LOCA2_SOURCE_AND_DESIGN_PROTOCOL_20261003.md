# LOCA2 U.S. source and design protocol

## Scope and estimand

The separate U.S. paper asks how high-resolution daily climate projections
alter crop-season precipitation quantity, timing, dry spells, and extremes,
and whether historically validated county crop responses differ by irrigation
status. LOCA2 supplies U.S./North American climate evidence; it does not
replace the global ISIMIP/GIVE path.

The agricultural response stage will compare mutually exclusive moisture
representations on identical samples and blocked holdouts: (i) seasonal
quantity, (ii) quantity plus preregistered distribution/extreme features, and
(iii) a drought-index family. Temperature controls are common to each family.
PDSI/SPEI will not be stacked with raw precipitation features and interpreted
as separate causal channels.

## Official source audit

The primary climate source is the USGS Water Mission Area STAC LOCA2 daily
Zarr collection. Its current consolidated metadata identifies daily `pr`,
`tasmin`, and `tasmax`; historical 1950--2014 and future 2015--2100 stores;
and precipitation version `v20240915`. The future precipitation array is
chunked one ensemble member at a time and in 468-day by 158-latitude by
118-longitude blocks. This supports bounded spatial/time reads.

Two USGS ScienceBase releases are relevant but not interchangeable:

- DOI `10.5066/P1N9IRWC` contains monthly county means and original threshold
  products based on an older LOCA2 precipitation version. Its principal
  county files are 1.87--3.11 GB. They are not the primary extreme-rain source.
- DOI `10.5066/P13FGPRM` updates precipitation extremes to LOCA2
  `v20240915`. Its county time-series NetCDF is 2.68 GB and contains annual
  metrics such as annual precipitation, Rx1day, Rx5day, Rx10day, maximum dry
  and wet spells, wet/dry-day counts, and percentile exceedances. These annual
  summaries are useful for climate validation, but they cannot substitute for
  crop-calendar daily features.

Both USGS data releases state CC0 1.0. The STAC catalog is public; the audit
must retain the dataset-specific source and rights rather than treating the
catalog's service license as a substitute.

## Source limitations frozen before analysis

1. LOCA2 is statistical downscaling. Fine grid spacing does not imply that
   local convective processes are dynamically resolved.
2. LOCA2 is trained on the unsplit Livneh observational product. Validation
   against Livneh would not be independent. The historical benchmark here is
   the existing NOAA nClimGrid-Daily county pipeline, while recognizing shared
   station and gridding influences.
3. LOCA2 interpolates source-model calendars to a standard calendar. Calendar
   identity and leap-day behavior must be checked before crop-year features.
4. The 2024 precipitation revision corrected a documented weakness in very
   high precipitation extremes, concentrated mainly in a western summer band.
   All precipitation work requires `v20240915`; older threshold products are
   descriptive legacy comparators only.
5. Official county products use TIGER 2023; the historical NASS/nClimGrid
   analysis uses TIGER 2019. GEOID matching and the existing historical-county
   exclusions must be reconciled explicitly.

## Outcome-blind ensemble and validation design

The primary ensemble gives each GCM equal weight, then divides that weight
equally across retained variants. Scenarios and variants are never counted as
independent GCMs. Every variant and scenario belonging to a source model stays
in the same five-fold model holdout. Fold assignment is deterministic from
`sha256(source_id)` and cannot use yields, damages, or SCC values.

Historical climate validation uses 1981--2000 for calibration diagnostics and
2001--2014 for a fixed temporal validation block on common county support.
Model weighting, if used beyond equal-GCM weighting, may use climate skill
only. The official CRIS 14-model weighting is a sensitivity only after its
exact weights and members are source verified.

The daily pilot will use fixed counties spanning humid rainfed, semiarid
rainfed, and irrigated production systems; fixed years; one model/member; and
only the Zarr chunks intersecting those selections. County and year selection
must be written before climate values are read. No NASS yield outcome may be
read during this pilot.

## Feature compatibility with the existing U.S. pipeline

Daily LOCA2 can reproduce the existing nClimGrid feature contract: crop-season
total precipitation, wet-day frequency and intensity, maximum dry spell,
Rx1day/Rx5day, stage shares, timing centroid, concentration, stage mean
temperature, and heat accumulation. Official monthly county summaries can
validate broad seasonal quantity and temperature, but not daily dry spells,
Rx5day, or exact stage features. Official annual extremes are retained as
independent climate-product checks, not as crop-season substitutes.

## Gates

The source audit gate opens only after the automated catalog receipt passes.
The climate-feature gate requires exact calendar, units, stage/season
reconciliation, county crosswalk, source hashes, bounded resource receipts,
and nClimGrid comparison. Outcome fitting remains separately closed. No result
may be called causal, monetized, or transported into an SCC until the relevant
gates are opened by new evidence and explicit authorization.

## Primary official references

- USGS revised precipitation extremes data release: https://doi.org/10.5066/P13FGPRM
- USGS county summaries data release: https://doi.org/10.5066/P1N9IRWC
- USGS Water Mission Area STAC LOCA2 catalog: https://api.water.usgs.gov/gdp/pygeoapi/stac/stac-collection/LOCA2?f=json
- LOCA project and version notes: https://loca.ucsd.edu/
- Pierce et al. (2023), *Journal of Hydrometeorology*: https://doi.org/10.1175/JHM-D-22-0194.1

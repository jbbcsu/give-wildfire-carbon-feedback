# U.S. post-2019 NASS county-outcome support, before yield estimation

## Result

The registered 2020–2025 [USDA NASS Quick Stats](https://www.nass.usda.gov/Quick_Stats/)
all-production-practices corn-grain/soybean snapshot contains 12 exact
crop-year responses and 16,544 API rows. After official county ANSI keys are
matched to the 2019 Census TIGER county identities, every matched row has a
positive reported yield. This is an **availability statement**; no yield
magnitude or climate-response coefficient is reported. NASS `COUNTY` responses
also contain aggregate/non-FIPS rows; these are counted but never assigned an
invented county.

| Crop | 2020 real-county positive outcomes | 2025 real-county positive outcomes | 2017 share ≤10%, 2020 / 2025 | Same screen AND existing crop-specific regional weather geography, 2020 / 2025 |
|---|---:|---:|---:|---:|
| Corn grain | 1,668 | 1,211 | 403 / 310 | 102 / 70 |
| Soybeans | 1,471 | 1,072 | 372 / 299 | 43 / 32 |

For a terminal **first-difference** test, a county must report positive yields
in consecutive years. Under both the fixed 2017 ≤10% irrigation-share screen
and the already constructed regional weather footprint, 2021–2025 annual
consecutive-pair counts are 85, 78, 69, 63, 52 for corn and 40, 39, 34, 22,
20 for soybean. This restricted geography is thin and increasingly selected.
The broader national screened outcome geography is materially larger but
requires an independent, consistent weather-exposure route. The <=20/30%
and 2022 irrigation-share-vintage counts are preserved in the full audit;
missing or suppressed irrigated acreage is never assigned a zero share.

The direct practice-specific NASS series are **not** a viable post-2019
terminal validation panel: after requiring positive values for both practices
in a real TIGER-matched county, corn has 1, 1, 3, 3, 1, 1 paired counties in
2020–2025; soybean has 3, 1, 3, 1, 1, 1. The all-practice outcome must not
be called observed rainfed yield. A small Census irrigated-area share is only
a transparent sample-selection proxy, not annual irrigation status or a
causal irrigation treatment.

The [NOAA nClimGrid-Daily product](https://www.ncei.noaa.gov/products/land-based-station/nclimgrid-daily)
offers daily precipitation and temperature through the present, and official
county averages as well as gridded fields. Before using this terminal NASS
sample, weather must be constructed with a consistent spatial estimator in
both training and test periods and the fixed crop-calendar rule. Source
revision, geography and outcome selection must remain visible. No 2020–2025
weather features or yield predictions were made in this stage.

## Reproduction and safeguards

- Design: `US_2020_2025_NASS_HOLDOUT_PROTOCOL_20260916.md`, SHA-256
  `f0b1384babe36d141dc349f767b03045a1c0a0fd94d2b58cbac47edd02389a71`.
- Credential-safe 12-object acquisition:
  `scripts/acquire_us_terminal_nass_outcomes.py`. Ignored summary
  `data/interim/nass_terminal_2020_2025_20260916/source/snapshot_summary.json`,
  SHA-256 `d735cf60d848b137b4b5a39a4a0b3bac0f9fd36862d5cf0ab9a51053cfb6049d`.
  The exact NASS API filters, per-object hashes, load-time fields and key-free
  SHA-512 manifest are retained locally. The acquisition took 49.97 seconds,
  peaked at 56.3 MB sampled RSS and added 21.5 MB. The saved API key was not
  written to any artifact.
- `scripts/audit_us_terminal_nass_support.py` checks source identities,
  matches official TIGER county GEOIDs, joins fixed 2017/2022 Census shares,
  intersects the old regional weather support and counts actual consecutive
  outcomes. Aggregate-only receipt:
  `data/interim/nass_terminal_2020_2025_20260916/support_audit/result.json`,
  SHA-256 `f0f61b660ffcf35b2dfb60e70631dedb8ef17bd2736805150eabb1e59a219964`.
- `scripts/validate_us_terminal_nass_support.py` independently rereads the
  source JSON with standard-library parsing, reconstructs TIGER/share/weather
  joins and both practice pairs, and passes 316 checks. Its first attempt
  failed only on treating an integer JSON `year` as a string and was retained;
  corrected receipt:
  `data/interim/nass_terminal_2020_2025_20260916/support_validation_v2/result.json`,
  SHA-256 `bd3a00e25a43cda29840948ef11c17af8b1e002c987f328cd1eb2de6a4cb1ea5`.
  Bounded audit/verification sampled RSS peaks were 294/235 MB, below 512 MB.

This is not a new empirical rainfall effect, observed rainfed yield, climate-
change attribution, adaptation estimate, economic loss, or SCC. Because
earlier model families and holdouts were inspected, the 2020–2025 period can
offer an additional temporal stress test, not a pristine confirmation of the
entire research design.

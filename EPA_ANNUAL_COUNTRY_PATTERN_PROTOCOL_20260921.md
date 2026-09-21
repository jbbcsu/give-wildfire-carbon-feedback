# Registered EPA annual precipitation country-pattern benchmark

## Purpose and boundary

Quantify the country-level annual-precipitation response to one kelvin of
global warming in the exact reviewed USEPA release. This is a published-method
external benchmark for the precipitation climate link. It is not the primary
crop exposure, a daily-weather emulator, an agricultural response, a damage
function, or an SCC estimate. It cannot represent crop calendars, rainfall
timing, dry spells, extremes, drought indices, irrigation, or adaptation.

## Frozen source

Use commit `dac5503549d5158e0257894012293acff45c0cb4` of
`USEPA/pattern-scaled-climate-variables` and only
`Precipitation/results/pattern_scaling_precipitation_by_country_full_sample.csv`.
Require SHA-256
`131fa989f43f3d9354da23eecf1cb647dc5c24399671e78fab93230d8902a013`.
The accompanying `make_patterns_for_give.R` must have SHA-256
`a4651abe5a743d7aa1fd2a22050ba3a3c267601524da4b9243a1a58967231241`.
The EPA repository labels code MIT and data/figures CC-BY-4.0. The raw CSV and
upstream license remain Git-ignored; aggregate code, protocol, and report may
be versioned.

EPA's script converts each PEEPS annual precipitation slope from
kg m-2 s-1 K-1 to mm yr-1 K-1 using `86400 * 365`, then aggregates to GIVE
countries. All five socioeconomic labels must contain identical
`patterns.area` values within every country/model group because the source
climate files are fixed to SSP2-4.5; failure of this identity rejects the
input. Select `ssp2` only after proving the five-label identity.

## Prespecified summaries

Require 23,920 rows, 184 ISO3 countries, 26 models, five scenario labels, and
4,784 country/model groups, with unique country/model/scenario keys. The first
registered run failed before output because the EPA file contains 405 missing
area-weighted values: 81 country/model pairs repeated across all five labels.
This source fact was not outcome-selected and is now a dated protocol
amendment. Require each country/model group to be either finite in all five
labels or missing in all five, reject infinities and partial-label support,
and never impute. Select `ssp2`, retain all 4,784 pairs with an explicit
availability flag, and calculate statistics from the 4,703 finite pairs.
Report available-model counts for every country and model. On that table:

1. For each country, record min, 5th, 25th, median, 75th, 95th, max, mean,
   standard deviation, positive-model fraction, negative-model fraction,
   available-model count, and missing-model count. Fractions use available
   models as their denominator.
2. Across the fixed 184-country set, count countries with positive, negative,
   or exactly zero ensemble medians; unanimous positive or negative signs;
   at least 80% positive or negative signs; 5th percentile above zero; and
   95th percentile below zero. These are country-count summaries, not
   land-, crop-, population-, or value-weighted global statistics.
3. For the three models overlapping the project's primary direct-daily set
   (MPI-ESM1-2-HR, MRI-ESM2-0, UKESM1-0-LL), report available country count,
   missing country count, country-count median,
   5th/95th percentiles, and sign fractions separately. Do not pool their
   slopes with crop-area-weighted daily-feature ratios.
4. Report the five largest and five smallest country ensemble medians only as
   a transparent spatial diagnostic fixed by rank, not as selected impact
   cases.

An independent implementation must reconstruct all country summaries and
aggregate counts from the frozen raw CSV. Nonfinite values, altered source
hashes, duplicate keys, missing models/countries, scenario-label disagreement,
or numerical disagreement fail closed. No FAIR path, crop yield, monetary
loss, existing-GIVE replacement, or SCC gate is opened by this benchmark.

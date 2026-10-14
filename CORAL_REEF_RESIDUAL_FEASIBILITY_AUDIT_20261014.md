# Residual coral-reef services: reproducibility and overlap audit

Status: bounded primary-source audit completed October 14, 2026. No coral
damage function or SCC is authorized for GIVE.

## Decision

There is now a published global coral SCC implementation with public derived
inputs, code, and outputs: Bastien-Olvera et al. (2026), implemented by the
Blue-SCC analysis repository and RICE50+ v2.6.0. This is a material advance
over the evidence available in the 2024 RFF ocean-systems report.

It is not yet transferable as an overlap-cleared GIVE component. Blue-SCC's
coral “non-market use” result combines eight ecosystem services. It publishes
no SCC or annual marginal-welfare path specifically for recreation and
tourism. Dividing or scaling the bundled result by value shares would be an
unsupported allocation, especially because the model embeds all ocean services
in a nonseparable CES utility function.

The shortest defensible route is therefore an author artifact request for a
service-disaggregated recreation/tourism run and additive annual country
welfare paths. The target is recreation/tourism consumer welfare only. Coral
fisheries, market provisioning, nonuse value, and reef-mediated coastal
protection remain excluded.

## Primary-source findings

### Blue-SCC and RICE50+

The peer-reviewed article is Bastien-Olvera et al., “Accounting for ocean
impacts nearly doubles the social cost of carbon,” *Nature Climate Change* 16,
297–304, DOI `10.1038/s41558-025-02533-5`. Its official availability statement
points to:

- `https://github.com/berbastien/blue-scc`, audited at commit
  `dbc0d8cb21c81f1508abfaf9e5c0f5671ccdd83f`; and
- `https://github.com/witch-team/RICE50xmodel/releases/tag/v2.6.0`, audited at
  commit `4003120a9e82ef2aebde57ac4fc84e8d034c9be3`.

The released coral response is a country-level linear relationship between
global mean surface temperature and coral-covered area, built from Sully et
al. projections and reef polygons. Country coral area and response
coefficients are published for 81 reef jurisdictions in
`corals_areaDam_Value.csv`; the RICE input stage combines those physical
responses with three valuation aggregates.

The Blue-SCC coral non-market-use aggregate is constructed from these annual
values in Int$2020/ha/year:

| Service | Value | In residual target? |
|---|---:|---|
| Climate regulation | 2 | No |
| Moderation of extreme events | 14,369 | No—coastal overlap |
| Waste treatment | 4,078 | No |
| Erosion prevention | 3,418 | No—coastal overlap |
| Maintenance of soil fertility | 1,551 | No |
| Aesthetic information | 5,580 | No—incidence not separately identified |
| Opportunities for recreation and tourism | 6,271 | Yes, but not released separately in SCC paths |
| Inspiration for culture, art and design | 917 | No—incidence not separately identified |
| **Bundled non-market use** | **36,186** | **No** |

The source assigns only a bundle-level standard error of 51,218 and a
category-level income elasticity of 0.222 (standard error 0.058). It does not
provide recreation-specific uncertainty or incidence. The published output
contains only `Corals / Market value`, `Corals / Non-market use value`, and
`Corals / Nonuse value` rows. Their numeric values are recorded in the machine
audit solely to identify the upstream artifact; they are not GIVE estimates or
candidate coefficients.

The country SCC table also cannot be treated as an additive regional
decomposition. Its 155 coral rows per valuation sum to values different from
the corresponding global rows. This is consistent with the source code using
country-specific consumption paths and discount normalization when
`country_level=True`. An author-provided additive attribution or, preferably,
matched annual baseline/pulse welfare paths is required.

Reproducibility remains partial:

- RICE50+ v2.6.0 contains the ocean module under GPL-3.0, but execution needs
  GAMS and an appropriate solver license.
- The Blue-SCC repository contains derived coral coefficients and final SCC
  tables, but no repository license file was found at the pinned commit.
- Its documented end-to-end preprocessing references `External_Data/` and
  `setup.r`, neither of which is present in the pinned tree. Consequently the
  derived country coefficients can be inspected, but their raw construction
  cannot be rerun from that repository alone.

### Other published candidates

| Source | Useful evidence | Blocking reason |
|---|---|---|
| Lane et al. (2013), PLOS ONE 8:e82579 | CC0 article; public COMBO model; explicit recreation consumer surplus and existence-value branches | Hawaii, South Florida, and Puerto Rico only; scenario comparison rather than a global marginal pulse; recreation is missing for Puerto Rico |
| Spalding et al. (2017), *Marine Policy* 82:104–113 | Global spatial reef-related tourism and expenditure evidence | Economic contribution/expenditure is not a complete welfare measure; no climate-response or marginal-pulse bridge |
| Brander et al. (2024), *Ecosystem Services* 66:101606 | Global synthesis and the service-specific mean used by Blue-SCC | Mixed local valuation concepts summarized per hectare; no climate response or SCC; summary mean alone is not transferable |
| Beck et al. (2018), *Nature Communications* 9:2186 | Global process-based avoided coastal flood damages; CC BY 4.0 article and downloadable results | Explicitly excluded from this residual because of the CIAM coastal-impact boundary; not a marginal temperature-pulse SCC |

No other audited source provides a global, marginal-pulse-compatible,
consumer-welfare coral-tourism component with public country-year inputs and
an explicit overlap boundary.

## Exact author artifact request

Please provide or publish:

1. A service-disaggregated recreation/tourism valuation table with study IDs,
   valuation method, beneficiary/incidence definition, units, price year,
   spatial mapping, uncertainty, checksums, and reuse license.
2. Recreation-specific income elasticity and uncertainty draws, or the exact
   joint draws used if the category-level elasticity is retained.
3. Country-year visits or participation, consumer surplus, beneficiary
   populations, and rules separating recreation from tourism expenditure,
   coastal protection, fisheries, nonuse, aesthetics, and cultural values.
4. Matched baseline and marginal-pulse country-year coral area and recreation
   welfare paths for every Monte Carlo draw.
5. Pulse year, magnitude, emissions units, normalization to USD/tCO2, climate
   draw IDs, socioeconomic draw IDs, discount draw IDs, and pairing rules.
6. Additive regional welfare contributions that reconcile exactly to annual
   global welfare, with an explanation of the current country/global SCC
   mismatch.
7. A license covering Blue-SCC code and derived data, plus the missing raw
   inputs and environment/setup files required for end-to-end reproduction.

## Minimum GIVE interface after receipt

The preferred interface is a table at `draw × path × country × year`, not a
headline SCC. Required fields are defined in
`config/coral_residual_candidate_audit_v1.json` and include pulse metadata,
coral area, recreation visits/participation, annual consumer surplus in 2020
USD, beneficiary population, income, discount factor, source version, license,
and overlap-boundary ID.

Admission requires matched baseline/pulse keys and fixed inputs, zero-pulse
and pre-divergence identities, exact country-to-global annual reconciliation,
and one-time insertion and discounting. The record must affirm that only
recreation/tourism consumer welfare is present.

Until then, the Blue-SCC coral results may be described only as published
external evidence. They must not be allocated, recalibrated, added to GIVE, or
presented as a reproduced residual coral SCC.

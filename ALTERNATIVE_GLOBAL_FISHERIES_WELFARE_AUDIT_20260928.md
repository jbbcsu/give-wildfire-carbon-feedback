# Alternative global fisheries welfare model audit

Date: 2026-09-28

## Decision

No screened primary-source model or official dataset supplies a defensible
combination of climate response, usable global geographic coverage, consumer
surplus, producer surplus, auditable inputs/code, usable licensing, marginal
CO2-pulse compatibility, and a resolved GIVE overlap boundary. No coefficient
transfer, fit, damage estimate, or SCC is authorized.

The closest integrated candidate is the climate-linked bioeconomic system in
Free et al. (2020), inherited from Gaines et al. (2018). It provides
country-level biomass, catch, and profit under climate and management
scenarios, but it fails the welfare and marginal-damage contract: consumer
surplus is absent; profit is not released as a separately validated producer
surplus measure; coverage is 779 single-species stocks in 156 coastal
sovereign countries and 58.2% of reported 2012 catch; source inputs needed by
the formatting code are absent; the repository has no explicit root license;
and the outputs are RCP/management scenarios rather than a matched marginal
emissions pulse.

## Primary-source screen

| Candidate | Climate and geography | Welfare supplied | Access/license | Pulse and overlap result |
|---|---|---|---|---|
| Free et al. 2020 / Gaines et al. 2018 | 779 single-species stocks, 156 coastal sovereign countries, 58.2% of reported 2012 catch; RCP and management scenarios | Biomass, catch, and profit (revenue minus fishing cost); no consumer surplus and no output explicitly identified and validated as producer surplus | Paper CC BY; public author repository, but no root license and two named raw inputs absent at pinned commit | Not a marginal pulse. Uniform range-share allocation does not establish producer, landing, trade, or consumer incidence. Nutrition, aquaculture, terrestrial substitution, and indirect effects are outside the boundary. |
| Moore et al. 2020 | 16 US fisheries, 56% of US commercial revenue; high/low climate scenarios | Consumer surplus only | Official NOAA copy is CC BY-NC 4.0; no reusable data/model package identified | Not global, no producer surplus, and no marginal pulse. |
| Speers et al. 2016 | Global coral-reef demand regions under RCPs; reef fisheries only | Consumer surplus only | Publisher full text restricted; no official reusable code/data archive identified | No producer surplus or marginal pulse; direct overlap risk with a coral-reef damage module. |
| Carozza et al. 2017 BOATS | Spatial global biomass/harvest/effort model, calibrated at LME scale | Fishing effort responds to grid-cell average profit; no demand or consumer surplus, and no separate producer-surplus output | Zenodo model dataset and MATLAB files are CC BY 4.0 | Archived calibration is not a climate-damage or pulse pair. Aggregated size groups lack country market/trade incidence. |
| Lam et al. 2016 | 887 species, 280 EEZs/high seas, 192 fishing nations, about 60% of reconstructed catch; RCP2.6/RCP8.5 | Maximum revenue potential (catch times ex-vessel price), not surplus | Open article/supplement; no official reusable licensed model/output repository identified in this bounded screen | Gross revenue is not welfare, RCP contrast is not a marginal pulse, and fleet location is not consumer incidence. |

Primary sources:

- Free et al. (2020), DOI: <https://doi.org/10.1371/journal.pone.0224347>;
  official author repository: <https://github.com/SFG-UCSB/cc_trade>
- Gaines et al. (2018), DOI: <https://doi.org/10.1126/sciadv.aao1378>
- Moore et al. (2020), DOI: <https://doi.org/10.1142/S2010007821500020>;
  NOAA record: <https://repository.library.noaa.gov/view/noaa/63753>
- Speers et al. (2016), DOI: <https://doi.org/10.1016/j.ecolecon.2016.04.012>
- Carozza et al. (2017), DOI: <https://doi.org/10.1371/journal.pone.0169763>;
  official Zenodo dataset: <https://doi.org/10.5281/zenodo.53934>
- Lam et al. (2016), DOI: <https://doi.org/10.1038/srep32607>

## Pinned Free/Gaines source result

The audit binds `SFG-UCSB/cc_trade` commit
`dfd250ddd806973f463e83097a3ed39dd27f8bfb` (2021-12-12) and hashes the
README, the main formatting script, and both released country CSVs.

- Both country CSVs contain 3,816 rows, 156 unique `sovereign_iso3` values,
  159 sovereign labels, four RCP labels, and six management scenarios.
- Their columns contain biomass/catch/profit summaries but no consumer- or
  producer-surplus field.
- All 56 tracked R/Rmd analysis files total only 275,939 bytes, and contain
  zero exact occurrences of `consumer surplus`, `consumer_surplus`,
  `producer surplus`, or `producer_surplus`.
- `code/Step1_format_gaines_data.R` requires
  `data/gaines/raw/eez_delta_k_df.rds` and
  `data/gaines/raw/global_cc_1nation_manuscript_2019Feb12.rds`; neither is in
  the pinned tree.
- The same script allocates global biomass, harvest, and profit to EEZs by
  species range share and explicitly documents the uniform-within-range
  assumption. That is a spatial allocation assumption, not evidence of fleet,
  landing, trade, producer, or consumer incidence.
- No `LICENSE`, `LICENCE`, or `COPYING` file exists at repository root. The
  article's CC BY license covers the article; it does not resolve the missing
  repository license gate for derivative model/data use.

The machine-readable receipt is
`data/provenance/alternative_global_fisheries_welfare_audit_20260928.json`.

## Exact external-data request

Ask the Free/Gaines model custodians for one versioned bundle containing:

1. An explicit redistribution and derivative-use license for the exact code
   and data release.
2. Checksum-pinned `eez_delta_k_df.rds`,
   `global_cc_1nation_manuscript_2019Feb12.rds`, and the raw
   realistic-adaptation counterpart used for the published outputs.
3. Executable model code and a dependency lock deriving annual stock-level
   biomass, harvest, prices, costs, effort, and profit from inputs.
4. Stock/species, EEZ/territory/sovereign, fleet/producer, landing, trade, and
   consumer-market keys, with high-seas, joint/disputed, missing, zero, and
   out-of-scope records explicitly distinguished. No pre-request imputation or
   renormalization is acceptable.
5. The demand system, baseline quantities/prices, elasticities or parameters,
   and direct consumer-surplus outputs, plus a statement and validation of
   whether modeled profit represents producer surplus/resource rent.
6. Same-model, same-realization annual baseline and one-ton-CO2-pulse outputs,
   or sufficient inputs and authorization to rerun them, with identical
   geographic, stock, and market masks.
7. An accounting boundary for aquaculture, terrestrial-food substitution,
   nutrition/mortality, coral services, and indirect/induced output effects.

Until that bundle passes the existing welfare and overlap interfaces, the
correct result is a documented negative feasibility finding, not an SCC.

## Reproduction

From an independently cloned repository at the pinned commit:

```bash
python3 scripts/audit_alternative_global_fisheries_welfare.py \
  --source-root /path/to/pinned/cc_trade
python3 test/test_alternative_global_fisheries_welfare.py
```

The audit reads the two small CSVs and 56 small source files without loading
the large RDS artifacts. It performs no model fit and no welfare or SCC
calculation.

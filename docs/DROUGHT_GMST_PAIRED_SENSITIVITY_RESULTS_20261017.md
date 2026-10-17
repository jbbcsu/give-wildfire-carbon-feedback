# Global maize drought/GMST paired GIVE sensitivity

## Result

The first paired GIVE calculation for the drought representation is complete.
At the registered 2% Ramsey schedule, the central historical response produces
`$0.0068975/tCO2` under fixed practice, `$0.0058294/tCO2` under trend
adaptation, and `$0.0045633/tCO2` under the upper-adaptation rule, all in 2020
USD.  Holding practice fixed, the historical-response interval gives
`$0.0021171--$0.0116779/tCO2`.  Positive values are damages.

These values are a **structural sensitivity**, not the paper's central
precipitation SCC.  The historical global association is 0.0210505 log yield
per one-unit SPEI-3 increase (interval 0.0064607--0.0356402).  The separate
five-ESM late-century endpoint fit is -0.1875848 SPEI-3 units per kelvin.  Their
product implies -0.00394875 log maize yield per kelvin in the central case.
The historical response did not show stable incremental country-holdout
prediction over rainfall, and the climate coefficient is a multi-forcing
late-century endpoint relationship rather than a transient CO2-only causal
response.  Those facts prevent promotion to a central causal estimate.

## Accounting and validation

The builder applies the mutually exclusive SPEI representation to 106
represented maize-producing countries, values national-market changes, and
maps them to GIVE's 16 FUND regions.  Antigua and Barbuda is excluded rather
than assigned to a guessed FUND region; its omitted baseline share is
`7.64e-8`.  Fixed, trend, and upper adaptation are crossed with the lower,
central, and upper historical response cases and four GIVE discount schedules.

The paired engine retains MooreAg's exact baseline agriculture damages and
global per-capita consumption, replacing only the marginal agriculture
response.  Both baseline errors are exactly zero.  All 36 SCC cells pass
regional installation, aggregation, currency conversion, response ordering,
adaptation ordering, and discount ordering checks.  The path builder's maximum
normalized 25,000-versus-50,000-tonne-carbon pulse discrepancy is `1.329e-4`,
below the registered `2e-4` convergence threshold.  The server run used the
archive's documented Julia 1.6.4 environment, peaked at 1.315 GB sampled group
RSS under a 3 GB cap, and completed all nine response/adaptation cases.

## Reproduction

- Path builder: `scripts/build_drought_gmst_fund_paths.py`
- Paired GIVE runner: `scripts/run_drought_gmst_replacement_sensitivity.jl`
- Independent validator: `scripts/validate_drought_gmst_replacement_sensitivity.py`
- Path provenance: `data/provenance/drought_gmst_fund_paths_v3_20261017.json`
- Validation: `data/provenance/drought_gmst_replacement_validation_v1_20261017.json`

The validated paired table is retained as an ignored intermediate artifact and
is bound by SHA-256 in the validation receipt.  Raw climate and socioeconomic
data are not committed.

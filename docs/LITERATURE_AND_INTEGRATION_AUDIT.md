# Literature and integration audit

## Coverage

Rennert et al. (2022, DOI `10.1038/s41586-022-05224-9`) describe GIVE's damage components as agriculture, mortality, energy, and coastal sea-level rise. Nonfatal temperature morbidity is not separately represented. This project excludes mortality, air pollution, infectious disease, labor productivity, and lost wages because those are covered or audited elsewhere.

An inspection of EPA FrEDI v4.1.1 confirms there is no general heat-morbidity sector. Its morbidity endpoints are attached to air pollution, Valley fever, vibriosis, wildfire, or crime; those are excluded here or cannot be decomposed without overlap. FrEDI's direct temperature sectors monetize mortality rather than nonfatal illness.

## Best national candidate: Lay et al. (2018)

Lay et al., *GeoHealth*, DOI `10.1002/2018GH000129`, estimate MSA-specific daily maximum-temperature relationships for commercially insured people age 64 and younger. Hyperthermia relationships pass the study's significance/FDR screen in 136 MSAs; cardiovascular outcomes did not pass broadly enough for projection. They combine five LOCA-downscaled CMIP5 models with RCP4.5/RCP8.5 and publish direct ED treatment expenditures using MEPS and Truven valuations. Holding population at 2010, the published climate-attributable projections range from 20,602 additional visits and $6.3-$37.5 million in 2050 under RCP4.5 to 65,136 visits and $19.8-$118.5 million in 2090 under RCP8.5 (2015 USD).

This endpoint is valuable because direct treatment expenditures can be separated from mortality and lost wages. It is not executable for GIVE from the publication artifacts: individual-level claims are confidential, fitted MSA spline objects are not released, and four RCP/year totals do not identify the marginal response to a small CO2 pulse. The covered population also excludes people 65+, uninsured people, Medicaid, rural residents outside modeled MSAs, and other groups. No adaptation is modeled.

## Best recent design: Gould et al. (2025)

Gould et al., *Science Advances*, DOI `10.1126/sciadv.adr3070`, estimate monthly California zip-code temperature-bin responses for the near-universe of ED visits and hospital admissions and project with 33 CMIP6 SSP2-4.5 simulations. The paper projects rising ED visits but declining admissions under warming, demonstrating why morbidity cannot be proxied by mortality. It propagates response resampling and climate-model uncertainty.

Code and nonprivate data are archived at Zenodo DOI `10.5281/zenodo.15691835` (resolved record version `16619660`). The archive contains projection/regression scripts and a processed temperature file, but the HCAI encounter records are restricted and fitted response/output objects are not supplied. The paper does not monetize visits. Therefore it is a strong design template, not an executable GIVE damage function.

## Why no numerical SCC is reported

Scenario-average future medical costs cannot identify the derivative of damages with respect to a marginal 2025 CO2 pulse. Fitting a temperature function to four RCP/year aggregates would conflate time, population, climate pattern, and scenario forcing. Scaling California results nationally or globally would ignore climate, baseline utilization, age, insurance, and adaptation heterogeneity. Either shortcut would create false precision.

## Integration contract

1. Secure released fitted response objects from the authors, or authorized HCAI/claims data to re-estimate them.
2. Construct area-month exposure counts in the published daily temperature bins under matched GIVE baseline and pulse climate realizations.
3. Multiply changes in utilization by a resource-cost measure for insurer plus out-of-pocket direct care. Treat payments and transfers consistently; exclude lost wages.
4. Keep pain, suffering, and consumer welfare separate unless supported by a morbidity-specific willingness-to-pay estimate.
5. Propagate epidemiological, climate-pattern, baseline-utilization, population, unit-cost, and adaptation uncertainty.
6. Validate temporal and spatial holdouts, hottest-region deletion, alternative bins/lags, and external claims datasets.
7. Only after these gates pass may the direct-medical component be added to GIVE; mortality, wages, and pollution remain excluded.

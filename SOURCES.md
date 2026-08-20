# Authoritative source register

| Use | Source | Why it is in scope |
|---|---|---|
| Physical basis, mean and heavy precipitation | [IPCC AR6 WGI, Chapter 11](https://www.ipcc.ch/report/ar6/wg1/chapter/chapter-11/) | Assessed basis for regional climate change and extremes. |
| CMIP6 scenario climate fields | [O'Neill et al. (2016), ScenarioMIP](https://doi.org/10.5194/gmd-9-3461-2016) | Primary protocol for scenario simulations. |
| CMIP6 design and ensemble | [Eyring et al. (2016)](https://doi.org/10.5194/gmd-9-1937-2016) | Primary CMIP6 experimental design. |
| Global daily bias-adjusted projections | [Lange (2021), ISIMIP3BASD](https://doi.org/10.5194/gmd-14-5443-2021) | Transparent bias-adjustment method for impact applications. |
| Crop-calendar inputs | [Jägermeyr et al. (2021), GGCMI Phase 3 calendar](https://doi.org/10.5281/zenodo.5062513) | Calendar-defined crop years and separate rice/wheat seasons. |
| Historical gridded yield outcomes | [Iizumi and Sakai (2020), GDHY](https://doi.org/10.1038/s41597-020-0433-7) | 0.5° annual, season-specific yield outcome; a census/satellite-informed estimate, not an independent FAOSTAT validation source. |
| Flood hazard/loss modeling | [Ward et al. (2020)](https://doi.org/10.1038/s41467-020-17591-w) | Global flood-risk modeling with climate and socioeconomic drivers. |
| River flood impacts and adaptation | [Winsemius et al. (2016)](https://doi.org/10.1038/nclimate2893) | Primary global assessment of flood-risk change and adaptation. |
| Climate and agricultural productivity | [Ortiz-Bobea et al. (2021)](https://doi.org/10.1038/s41586-021-03500-5) | Empirical global agricultural productivity response to climate change. |
| US hourly rainfall-intensity response | [Lesk, Coffel, and Horton (2020)](https://doi.org/10.1038/s41558-020-0830-0) | County maize/soy yield study that estimates a nonlinear response to the distribution of growing-season hourly rainfall intensities and provides code/data links. |
| US excessive-rainfall loss | [Li et al. (2019)](https://doi.org/10.1111/gcb.14628) | Observational US maize/insurance evidence that very wet conditions can reduce yields; supports wet-excess metrics alongside drought metrics. |
| US extremes and irrigation | [Troy, Kipgen, and Pal (2015)](https://doi.org/10.1088/1748-9326/10/5/054013) | County-level US crop/yield analysis of growing- and planting-season extremes, including a limited irrigated/rainfed subset. |
| Rainfall amount, frequency, intensity, and onset | [Guan et al. (2015)](https://doi.org/10.1002/2015GL063877) | Synthetic-rainfall, two-crop-model West Africa experiment that separates amount, frequency/intensity, and monsoon timing; a process-model benchmark, not an econometric coefficient source. |
| Stage-wise dry/wet sequences | [Marcos-Garcia, Carmona-Moreno, and Pastori (2024)](https://doi.org/10.1038/s43016-024-01040-8) | Sub-Saharan African maize/GDHY analysis of within-growing-season dry/wet spell patterns; directly relevant feature and validation benchmark. |
| Calendar adaptation under climate change | [Minoli et al. (2022)](https://doi.org/10.1038/s41467-022-34411-5) | Global process-model counterfactuals for sowing/maturity adaptation across crop calendars and climate scenarios. |
| Rainfall amount and rainy-day distribution | [Fishman (2016)](https://doi.org/10.1088/1748-9326/11/2/024004) | Indian daily rainfall/crop-yield evidence separating total precipitation from rainy-day frequency; a core feature-design precedent, not a transferable coefficient. |
| Drought-index robustness | [Drought metrics plan](DROUGHT_METRICS_PLAN.md) | PDSI/SPEI/soil-moisture implementation, non-collinearity, calibration, and SCC-attribution rules. |
| Observed US drought/yield validation | [Kuwayama et al. (2019)](https://doi.org/10.1093/ajae/aay037) | County fixed-effect USDM drought-severity-week benchmark for NASS yield validation; USDM is not projected directly in global SCC draws. |
| Irrigation constrained by water availability | [Fishman literature screen](FISHMAN_EVIDENCE_NOTE.md) | Documents use of Fishman and collaborators' irrigation/groundwater evidence for adaptation constraints and accounting boundaries. |
| Supplied irrigated-water evidence | [Project assessment note](IRRIGATED_WATER_EVIDENCE_NOTE.md) | Documents the limited, non-stacking use of the supplied Gordon-Blumberg and Blumberg-Warziniack US manuscripts for irrigation/water-supply design. |
| Existing GIVE methods | [Rennert et al. (2022)](https://doi.org/10.1038/s41586-022-05224-9) | Baseline GIVE SCC framework and sectoral design. |
| Potentially overlapping GIVE precipitation work | [Wenz et al. (2024) working paper](https://doi.org/10.21203/rs.3.rs-4829018/v1) | Novelty/overlap gate; do not stack its aggregate productivity damages with this sectoral module. |

These sources justify architecture and input selection; they do not by
themselves identify a transferable precipitation-damage coefficient.  Any
calibration dataset must have its own license, version, spatial coverage, and
provenance record before use.

# GIVE damage-sector evidence registry

Status date: 13 October 2026. Values below retain their source configuration and
are not mutually additive unless explicitly stated.

| Pathway | Current evidence | Estimate/status | Integration state | Fastest defensible next step |
|---|---|---|---|---|
| Temperature mortality | Existing GIVE sector | Existing model component | Baseline | Preserve; audit overlap with labor and air pollution |
| Agriculture, total | Moore et al. (2026), DOI [10.1038/s41558-026-02749-z](https://doi.org/10.1038/s41558-026-02749-z) | Locally reproduced 10,000-draw means: $29.05/tCO2 Lancet and $29.10/tCO2 ISO; equal-function mean $29.07 reproduces the published rounded $29 | Both structural specifications reproduced; replacement/overlap review remains | Replace legacy GIVE agriculture without adding the precipitation module wholesale |
| Agriculture, precipitation quantity/timing | Original isolated precipitation project | One-model monthly maize diagnostic: +$0.004269/tCO2 in 2020 USD at 2%; 77.4% of gross country magnitude cancels; not total precipitation-agriculture damages | Original bounded diagnostic; non-additive to total agriculture | Complete drought attribution, multi-model climate response, irrigation, other crops, and replacement design |
| Agriculture, drought/timing/extremes | Original global and U.S. validation tracks | U.S. non-irrigated corn: -4.30% yield per one-unit PDSI decline, 500 km interval -5.02% to -3.57%; five-model late-century U.S. SPEI-3 contrasts are all negative | Historical PDSI association and future SPEI exposure separately validated; all 11 missing historical cells and the first of 15 future cases are validated, so the county bridge remains closed | Complete the remaining 14 future extrema cases sequentially, then build and validate same-source county SPEI on NASS calendars |
| Labor productivity | Moore et al. (2026) | Locally reproduced 10,000-draw means: $29.26/tCO2 Lancet and $51.86/tCO2 ISO; equal-function mean $40.56 reproduces the rounded $41 headline | Both structural specifications reproduced; cross-function quantiles and overlap-cleared GIVE installation remain open | Install paired labor component; retain $29.26-$51.86 structural range and do not invent pooled quantiles |
| Fisheries market + nutrition | Bastien-Olvera et al. (2025/2026), DOI [10.1038/s41558-025-02533-5](https://doi.org/10.1038/s41558-025-02533-5) | Published benchmark: $22.09755/tCO2 ($0.05704 market; $22.04051 nutrition/use) | External, non-additive; complete nutrition inputs cover only 116/184 GIVE countries and 4/16 regions; released nutrition country sum differs 4.92% from Figure 4, while market country rows differ -7.67%; RICE50x pulse outputs unavailable | Obtain licensed versioned RICE50x baseline/pulse artifacts and additive country decompositions, resolve missingness/output discrepancies, then allocate nutrition/mortality and market endpoints once |
| Biodiversity nonuse | Published benchmark audited in isolated biodiversity project | Approximately $8/tCO2; published external benchmark | External, non-additive; regional coefficients/joint draws unavailable locally | Obtain coefficients and joint uncertainty, then audit overlap with reef/nonuse values |
| Coastal flooding | Existing GIVE/CIAM sector | Existing model component | Baseline | Preserve; exclude coastal protection from new flood and reef modules |
| Inland riverine/pluvial flooding | Literature/data screen only | No promoted SCC | Open research gap | Defer until precipitation agriculture replacement is stable |
| Building energy | Existing GIVE sector | Existing model component | Baseline | Preserve; audit adaptation-energy overlap with labor heat exposure |
| Surface ozone health | McDuffie et al. (2026), DOI [10.1021/acs.est.5c14713](https://doi.org/10.1021/acs.est.5c14713) | Published global mean +$23/tCO2 at 2% Ramsey; 90% interval +$7 to +$45 | Official MIT code acquired; checked-in RFF/mean-path ozone summaries are +$16.67/+20.66 and do not reproduce the article; final release and price-year reconciliation requested | Obtain the versioned final artifacts, reproduce same-run annual paths, then audit mortality overlap |
| Non-wildfire meteorological PM2.5 health | McDuffie et al. (2026) | Published global mean -$38/tCO2 at 2% Ramsey; 90% interval -$118 to -$3 | Checked-in RFF/mean-path PM summaries are -$24.53/-21.91; released RFF component sum differs from its separate net by -$26.81/tCO2; wildfire exclusion and price-year metadata remain unresolved | Obtain the final same-run component/net release and machine-readable wildfire exclusion; do not calibrate checked-in outputs to the article |
| Wildfire smoke PM2.5 mortality | Williams et al. draft supplied by the investigator (9 October 2026) | Provisional global mean $50/tCO2; 95% conditional interval $18.5-$102.6; 2025 pulse and 2% discounting | Unpublished external module; not yet additive | Reproduce the draft's country coefficients and Monte Carlo result; audit mortality valuation and shared fire-climate inputs |
| Wildfire CO2 feedback | Separate wildfire-carbon project | Separate paper and codebase | External until final interface is reviewed | Import only its reviewed marginal-damage output; never modify its files here |
| Coral reef services | RFF priority pathway | No mutually exclusive local SCC | Open research gap | Allocate fisheries, nonuse, coastal protection, and tourism once |
| Municipal water systems | Future drought/water-supply pathway | No promoted SCC | Deferred research gap | After agricultural drought: screen scarcity, treatment, pumping, and infrastructure costs while excluding household adaptation already captured elsewhere |

## Authorized integration order

1. Replace legacy GIVE agriculture and add labor using the reproducible Moore
   et al. package.
2. Add wildfire smoke PM2.5 mortality after reproducing the investigator's
   global draft module and resolving overlap with existing mortality. Add the
   separate wildfire-carbon feedback only after importing its final reviewed
   marginal-damage output through a documented interface. Shared fire-climate
   inputs must be identified, but the two distinct endpoints - air-pollution
   mortality and additional atmospheric CO2 - are valued only once.
3. Add fisheries after reproducing the published paths and allocating its
   nutrition/mortality and market endpoints against existing GIVE sectors.
4. Estimate drought and other precipitation-pattern effects on agriculture as
   an incremental correction to the Moore agriculture replacement, not as a
   second total agriculture sector. Total precipitation, timing, dry spells,
   extremes, and drought indices compete in pre-specified models; irrigation
   is treated explicitly where data permit.
5. Develop municipal drought and water-supply damages later.
6. Replicate the published EPA meteorological air-pollution model, which
   reports +$23/tCO2 for surface ozone and -$38/tCO2 for non-wildfire PM2.5 at
   2% Ramsey discounting. The acquired public commit predates the final article
   and its summaries do not reproduce those values, so neither is promoted.
7. Screen the remaining RFF-identified omissions, prioritizing biodiversity,
   inland extreme-weather/flood damages, coral reefs, and other ocean services.
   Only reproducible, overlap-cleared pathways enter a combined SCC.

## Non-negotiable combination rule

The synthesis will report three quantities rather than one premature grand
total: (i) the existing GIVE SCC; (ii) the SCC after locally replicated,
overlap-cleared replacements/additions; and (iii) a non-additive evidence
envelope containing original bounded estimates and published external
benchmarks. This prevents missing sectors from being treated as zero without
pretending that overlapping partial SCCs can be summed.

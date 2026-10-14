# GIVE damage-sector evidence registry

Status date: 14 October 2026. Values below retain their source configuration and
are not mutually additive unless explicitly stated.

| Pathway | Current evidence | Estimate/status | Integration state | Fastest defensible next step |
|---|---|---|---|---|
| Temperature mortality | Existing GIVE sector | Existing model component | Baseline | Preserve; audit overlap with labor and air pollution |
| Agriculture, total | Moore et al. (2026), DOI [10.1038/s41558-026-02749-z](https://doi.org/10.1038/s41558-026-02749-z) | Locally reproduced 10,000-draw means: $29.05/tCO2 Lancet and $29.10/tCO2 ISO; equal-function mean $29.07 reproduces the published rounded $29 | Both structural specifications reproduced; replacement/overlap review remains | Replace legacy GIVE agriculture without adding the precipitation module wholesale |
| Agriculture, precipitation quantity/timing | Original isolated precipitation project | One-model monthly maize diagnostic: +$0.004269/tCO2 in 2020 USD at 2%; 77.4% of gross country magnitude cancels; not total precipitation-agriculture damages | Original bounded diagnostic; non-additive to total agriculture | Complete drought attribution, multi-model climate response, irrigation, other crops, and replacement design |
| Agriculture, drought/timing/extremes | Original global and U.S. validation tracks | U.S. non-irrigated corn: -4.30% yield per one-unit PDSI decline, 500 km interval -5.02% to -3.57%; five-model late-century U.S. SPEI-3 contrasts are all negative | Historical PDSI association and future SPEI exposure separately validated; all 11 missing historical cells and 5 of 15 future cases are validated, so the county bridge remains closed | Complete the remaining 10 future extrema cases sequentially, then build and validate same-source county SPEI on NASS calendars |
| Labor productivity | Moore et al. (2026) | Locally reproduced 10,000-draw means: $29.26/tCO2 Lancet and $51.86/tCO2 ISO; equal-function mean $40.56 reproduces the rounded $41 headline | Source-verified paired-module preflight passes for separate Lancet and ISO cases, but target GIVE execution is unrun; the legacy agriculture branch reached 2,531,426,304 bytes (2.36 GiB), above the 512 MiB worker cap | Run separate target cases on an authorized >2.36 GiB worker; retain the structural range and case-specific quantiles, and do not promote a replacement delta or pooled uncertainty |
| Fisheries market + nutrition | Bastien-Olvera et al. (2025/2026), DOI [10.1038/s41558-025-02533-5](https://doi.org/10.1038/s41558-025-02533-5) | Published benchmark: $22.09755/tCO2 ($0.05704 market; $22.04051 nutrition/use) | External, non-additive; the annual-pair gate rejects the public terminal summaries: 0 of 2 comparable fisheries rows reconcile additively, and matched annual baseline/pulse paths, pulse metadata, direct CS/PS semantics, complete mapping, and boundary/license records are absent | Obtain a licensed package of matched annual RICE50x baseline/pulse paths satisfying the frozen admission contract, then allocate nutrition/mortality and market endpoints once |
| Biodiversity nonuse | Wingenroth et al. (2024) public-release audit | Approximately $8/tCO2; published external benchmark | External, non-additive; the pinned public evidence supplies 0 of 7 required artifact groups, so the executable admission gate rejects it as incomplete | Obtain all seven source, calibration, mapping, joint-draw, pulse-output, provenance/license, and welfare-boundary artifact groups; then reproduce before overlap review |
| Coastal flooding | Existing GIVE/CIAM sector | Existing model component | Baseline | Preserve; exclude coastal protection from new flood and reef modules |
| Inland riverine/pluvial flooding | Literature/data screen only | No promoted SCC | Open research gap | Defer until precipitation agriculture replacement is stable |
| Building energy | Existing GIVE sector | Existing model component | Baseline | Preserve; audit adaptation-energy overlap with labor heat exposure |
| Surface ozone health | McDuffie et al. (2026), DOI [10.1021/acs.est.5c14713](https://doi.org/10.1021/acs.est.5c14713) | Published global mean +$23/tCO2 at 2% Ramsey; 90% interval +$7 to +$45 | External, non-additive; checked-in RFF ozone is +$16.671649, while the released component sum (-$7.857400) and separate net (-$34.667618) differ by -$26.810218/tCO2; final-release, same-stream, price-year, boundary, reproduction, transfer, and replacement gates remain closed | Obtain the versioned final artifacts and same-run annual ozone/PM/net paths, resolve the price year, then audit mortality overlap |
| Non-wildfire meteorological PM2.5 health | McDuffie et al. (2026) | Published global mean -$38/tCO2 at 2% Ramsey; 90% interval -$118 to -$3 | External, non-additive; checked-in RFF PM is -$24.529049. The article excludes open burning, but the repository lacks machine-readable exclusion metadata and mixes 2024-dollar inputs with 2020-dollar headers; all promotion gates remain closed | Obtain the final same-run component/net release, explicit price-year conversion, and machine-readable wildfire/open-burning exclusion; do not calibrate checked-in outputs to the article |
| Wildfire smoke PM2.5 mortality | Williams et al. draft supplied by the investigator (9 October 2026) | Provisional global mean $50/tCO2; 95% conditional interval $18.5-$102.6; 2025 pulse and 2% discounting | Unpublished external module; not yet additive | Reproduce the draft's country coefficients and Monte Carlo result; audit mortality valuation and shared fire-climate inputs |
| Wildfire CO2 feedback | Separate wildfire-carbon project | Separate paper and codebase | External until final interface is reviewed | Import only its reviewed marginal-damage output; never modify its files here |
| Coral reef residual services | Bastien-Olvera et al. (2026) Blue-SCC public-release audit | Published external coral non-market-use benchmark: $2.46/tCO2; bundles eight services | External, non-additive; recreation/tourism is not released separately, CES share-scaling is unsupported, country rows do not reconcile to the global result, and fisheries/nonuse/coastal overlaps remain | Obtain service-disaggregated recreation/tourism welfare paths and additive country-year baseline/pulse artifacts; exclude provisioning, nonuse, and coastal protection |
| Municipal water systems | Dolan et al. (2021) GCAM, MimiFUND v3.13.0, and CLIMADA/GloFAS fast-route audit | No promoted SCC; 0 of 3 candidates pass all seven transfer gates | Documented external gap: GCAM combines six water-demand sectors and lacks a marginal-pulse path; FUND water is aggregate rather than municipal; GloFAS is a fluvial physical comparator without annual welfare | Request licensed GCAM curves, municipal-only CS+PS decomposition, annual matched pulse paths, and a conserving basin-to-GIVE map; do not allocate mixed water surplus by shares |
| Heat-driven road and rail infrastructure | EPA FrEDI v4.1.1; Kopits et al. (2025) Tables A.1-A.3 | No promoted SCC | Newly named authoritative-scope gap; pinned public CONUS response functions are marginal-path compatible, but no local reproduction or global transfer is validated | Reproduce annual road-repair, road-user, rail-replacement, and rail-delay endpoints separately; exclude flood/coastal endpoints and audit time-delay overlap with labor |
| Electricity supply and grid infrastructure | EPA FrEDI v4.1.1 | No promoted SCC | Newly named authoritative-scope gap; generation/capacity and transmission/distribution are distinct from GIVE building demand, but component additivity and global transfer are unvalidated | Reproduce supply and grid endpoints only; exclude building heating/cooling expenditure and reconcile repair, capacity, efficiency, and interruption costs |
| Climate-sensitive infectious disease and selected morbidity | EPA FrEDI v4.1.1; Kopits et al. (2025) Tables A.1-A.3 | No promoted SCC | Newly named authoritative-scope gap; selected CONUS endpoints are public, but the global category is incomplete and mortality overlap is unresolved | Reproduce Valley fever and vibriosis mortality/morbidity separately; keep suicide closed under FrEDI's explicit double-count warning and do not extrapolate outside CONUS |

## Authorized integration order

1. Execute the source-verified Moore paired-module plan as separate Lancet and
   ISO cases on an authorized worker above the observed 2.36 GiB requirement.
   Replace legacy agriculture and add labor only after target-graph validation;
   do not pool quantiles or promote the staged replacement delta.
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

## Authoritative missing-scope reconciliation

The bounded 14 October 2026 reconciliation against the RFF-led GIVE paper,
EPA's 2023 scope table, and the EPA NCEE GIVE/DSCIM/FrEDI crosswalk found real
registry gaps. The three fastest screenable sector candidates are now named
above. Other still-untracked or only partially tracked categories are
displacement and migration outside coastal CIAM, human capital, livestock,
forestry and timber, broader tourism/recreation/aesthetics, other provisioning,
regulating and cultural ecosystem services, crime, conflict/national security,
and trade/logistics/supply-chain spillovers. Large-scale Earth-system feedbacks
beyond the separate wildfire-carbon project are a cross-module gap rather than
a damage sector. See
[the source-specific audit](RFF_GIVE_MISSING_SCOPE_AUDIT_20261014.md) and its
[machine-readable crosswalk](data/provenance/rff_give_missing_scope_audit_20261014.json).

## Non-negotiable combination rule

The synthesis will report three quantities rather than one premature grand
total: (i) the existing GIVE SCC; (ii) the SCC after locally replicated,
overlap-cleared replacements/additions; and (iii) a non-additive evidence
envelope containing original bounded estimates and published external
benchmarks. This prevents missing sectors from being treated as zero without
pretending that overlapping partial SCCs can be summed.

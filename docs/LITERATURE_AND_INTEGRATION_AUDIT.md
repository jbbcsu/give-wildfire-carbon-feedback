# Permafrost carbon feedback audit

## Coverage finding

The exact GIVE source constructs MimiFAIRv1_6_2 and routes socioeconomic CO2 and CH4 through identity components into FaIR's CO2 and CH4 cycles. The CO2 cycle contains a temperature-dependent adjustment to carbon uptake (`rT_co2`), but neither the component nor GIVE contains an explicit frozen-carbon pool, thaw process, or permafrost emission stream. The CH4 cycle adds fossil and prescribed natural emissions; GIVE connects its socioeconomic CH4 path to the fossil-emissions port.

This code reading is consistent with EPA/NCEE's 2025 technical appendix, which explicitly states that permafrost thaw and Amazon dieback are not represented in FaIR 1.6.2 and adds their emissions to FaIR in the subsequent year. The distinction matters: temperature-dependent sink weakening is not the same state variable as emissions from a previously frozen stock.

## Literature-first model choice

### Preferred interface candidate: PerCX

Steinert and Sanderson (2025; DOI `10.5194/esd-16-1711-2025`) publish PerCX, a compact temperature-history-to-CO2/CH4-emissions response model coupled in the paper to FaIR 1.6.4. The model uses a finite initial permafrost carbon pool, exponential response kernels, CO2 and CH4 response amplitudes, and a response timescale. It is constrained against the AR6 range under CMIP6 SSP2-4.5 and tested against UVic. Code and parameters are archived as version 1.0.1 at DOI `10.5281/zenodo.17279654` under Apache-2.0. The exact source, parameter table, and license are vendored with hashes.

PerCX is architecturally closer to GIVE than substituting a different climate model: it produces annual CO2 and CH4 emissions from GMST and was designed to feed those emissions to FaIR. It also preserves a finite pool rather than treating every degree-year as an unlimited permanent source.

### Alternative benchmarks

Gasser et al. (2018; DOI `10.1038/s41561-018-0227-0`) implement a permafrost module in OSCAR and establish path dependence in remaining carbon budgets. OSCAR is open and provides an independent dynamic benchmark, but replacing GIVE's FaIR climate module would change many processes at once.

Dietz et al. (2021; DOI `10.1073/pnas.2103081118`) implement permafrost and other feedbacks in the open META architecture. EPA/NCEE later adapted that approach to modified MimiGIVE. This is powerful precedent, but the reported 9–50 percent increase in U.S.-specific SCC combines permafrost and Amazon feedbacks and varies across underlying damage models. It cannot be used as a permafrost-only scalar.

## Release audit findings

The archived PerCX v1.0.1 parameter file contains 765 parameter rows, while the final article states that 775 of 1,000 sampled combinations were retained. The released source accepts `decay_rate` and the parameter file contains `decay`, but the function body does not use that argument. These may be benign versioning or vestigial-calibration details, but they must be reconciled before declaring exact article replication.

The vendored implementation passes basic software sanity checks: a zero-temperature path generates zero emissions; nonnegative warming and positive parameters produce nonnegative emissions; and the combined emitted carbon never exceeds the initial pool. These checks validate mechanics only, not calibration or GIVE coupling.

## Required GIVE architecture

For each Monte Carlo draw and for both baseline and marginal-pulse runs:

1. Read GMST through year `t` from FaIR.
2. Compute PerCX CO2 and CH4 fluxes using the same permafrost parameter draw in both runs.
3. Add those fluxes to emissions entering FaIR in year `t+1`, preserving the published lag and avoiding an algebraic loop.
4. Recompute concentrations, forcing, temperature, and every downstream damage.

CO2 output in PgC/yr is numerically GtC/yr and can enter FaIR's `E_co2`. PerCX CH4 is carbon mass and must be converted to methane mass: `MtCH4 = PgC * 1000 * 16/12`. It should not simply be added to GIVE's `fossil_emiss_CH4` port. Permafrost methane is biogenic; routing it as fossil affects methane-oxidation bookkeeping. A dedicated natural/additional methane channel and explicit oxidation treatment are required.

## Double-counting and baseline gates

- The explicit permafrost feedback is absent from FaIR 1.6.2, but each RFF-SP/SSP emissions source must still be verified to exclude permafrost emissions.
- FaIR's generic temperature-dependent uptake must remain unless a calibration exercise shows that adding PerCX requires retuning; removing it would discard ordinary land/ocean carbon-cycle feedbacks.
- Do not add infrastructure, erosion, ecosystem, or biodiversity damage from thaw in this climate-feedback module.
- Keep wildfire carbon entirely outside this repository and reconcile combined feedbacks only in a higher-level climate-module branch.

## Validation before SCC use

The integration must reproduce published PerCX/FaIR trajectories, compare against OSCAR or another permafrost-enabled model, and pass mass balance, zero feedback, zero pulse, pre-pulse identity, decreasing pulse-size convergence, and common-random-number checks. Parameter dependence between FaIR sensitivity and permafrost response should be tested rather than assumed absent.

Until these gates pass, the only defensible output is this readiness scaffold. No permafrost SCC or fixed percentage uplift is authorized.

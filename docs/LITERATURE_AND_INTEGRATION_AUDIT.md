# Literature and integration audit

## What GIVE already represents

GIVE uses MimiFAIR v1.6.2 with separate `fossil_emiss_CH4` and `natural_emiss_CH4` inputs. The natural input comes from `fair_wg3_natural_ch4_n2o.csv`. It is fixed at 168.83862060475192 Mt CH4/year from 2015 through 2300. Therefore the model contains a calibrated natural methane baseline but no explicit warming-, precipitation-, or inundation-sensitive wetland feedback after 2015.

That distinction controls double counting. A wetland module must replace the wetland portion of the natural baseline or add only a climate-driven anomaly relative to a consistently defined anchor. Adding an absolute wetland flux on top of the full natural series would double count baseline wetlands.

## Shortest published benchmark

Sloughter et al. (2026; DOI 10.5194/gmd-19-9063-2026) implement natural wetland methane in MAGICC v7.6 as

`E_wetland = m * T + E0`,

with a normal slope distribution of 30 +/- 13 Mt CH4/year/K. Fits reported in the paper are 35.5 for Zhang et al. (2017), and 37.5, 45.8, and 52.6 Mt CH4/year/K for Kleinen et al. (2021) when ending the calibration in 3000, 2500, and 2300. MAGICC is concentration constrained through 2015 and applies the emissions feedback thereafter.

This is directly compatible with a lightweight annual recursion and is the primary readiness benchmark. It is not yet a GIVE result. The model authors explicitly describe GMST as a proxy for precipitation, expanding tropical wetland area, and other entangled processes. They find reversibility questionable beyond 2100 and note recent models spanning from near-zero to high sensitivity.

The untruncated normal distribution assigns approximately 1.05% probability to a negative slope. The published lower bound is not clearly constrained, so truncation would be a modeling choice rather than a clerical fix and must be prespecified.

## Process and observational comparators

Zhang et al. (2017; DOI 10.1073/pnas.1618765114) and Kleinen et al. (2021; DOI 10.1088/1748-9326/ac2f66) provide the global scenario simulations behind the MAGICC calibration. OSCAR v3.1 is an open alternative with wetland area responding to CO2, local temperature, and precipitation and emissions intensity tied to land-carbon processes, but it is a much larger coupled model and its wetland calibration is inherited from WETCHIMP/CMIP5-era evidence. Chang et al. (2021; DOI 10.1038/s41467-021-22452-1) shows observed hysteresis in emergent wetland temperature sensitivity. IPCC AR6 assesses a wetland CH4-climate feedback of 0.03 +/- 0.01 W/m2/K, with limited evidence but high agreement; that forcing metric is useful for validation, not direct addition to an emissions-driven SCC.

## GIVE-specific hard gate: source attribution

The GIVE FaIR methane component computes oxidized methane carbon using a `fossil_frac` parameter. The GIVE setup sets this fraction to one. Adding climate-sensitive wetland methane to atmospheric burden without source-resolved bookkeeping would therefore classify biogenic methane oxidation as fossil carbon and inject inappropriate CO2. Wetland emissions must enter `natural_emiss_CH4`, never `fossil_emiss_CH4`, and the oxidation calculation must track the fossil share of burden dynamically.

The methane step also evaluates the natural input at the current time in both the previous- and current-emissions terms, whereas fossil emissions use previous and current time indices. Before a dynamic natural series is connected, this convention must be reconciled and its timing tested. A safe initial contract is for temperature through t-1 to determine wetland emissions at t, avoiding a same-timestep temperature-emissions algebraic loop.

## Marginal-pulse contract

Baseline and pulse runs must use the same wetland slope and all shared FaIR parameters. Each run recursively generates its own lagged wetland-emissions anomaly from its own temperature path. Both must have identical history through the pulse year. Absolute historical/natural emissions must remain concentration-calibrated. The implementation must pass zero-feedback, zero-pulse, pre-pulse identity, pulse-size convergence, source-specific oxidation, unit, timestep, and horizon tests.

## Decision

The new 2026 MAGICC function makes the scientific path materially shorter: a source-pinned global reduced form exists. Integration still fails closed until the natural baseline/intercept and biogenic oxidation boundaries are solved. No published temperature or forcing increment is converted into an SCC scalar.


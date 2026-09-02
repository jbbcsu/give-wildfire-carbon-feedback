# Literature audit: climate-to-precipitation emulation

Updated: 2026-08-26

## Decision

Do **not** develop a free-standing precipitation emulator from scratch. The
project owner selected the direct daily ISIMIP3b crop-feature response route as
primary on 25 August 2026: derive the exact crop-calendar features from
version-pinned ESM/member fields, fit ESM-specific feature responses to
same-realization GMST, and evaluate matched GIVE/FAIR baseline and pulse paths
with common residual innovations. Several peer-reviewed, open or archived
frameworks already emulate spatial precipitation along novel warming
trajectories; they are benchmarks or fallbacks, not evidence that
climate-to-rainfall emulation is a new contribution here.

No peer-reviewed publication identified so far provides all required outputs:
globally coherent crop-window totals, daily wet/dry persistence,
heavy-rainfall tails, joint temperature--precipitation dependence, and a
stable mapping for a small matched baseline/pulse SCC perturbation. A July
2026 preprint comes close on the climate side, but has not yet cleared peer
review or crop-feature validation. The remaining gap is therefore an
integration, validation, and economic-attribution problem, not a claim that
precipitation emulation itself is new.

## Directly relevant systems

| System | Published capability | Use here | Material limitation |
|---|---|---|---|
| RIG, Huang et al. (2026 preprint), https://doi.org/10.48550/arXiv.2607.21382 | Uses response theory plus a guided diffusion model to produce joint, bias-corrected global daily temperature and precipitation at 0.25 degrees under flexible radiative-forcing scenarios, including long horizons. | Closest known end-to-end climate candidate; evaluate first as an external benchmark and possible future primary driver. | Submitted 23 July 2026 and not peer reviewed; source and trained model are promised only upon publication; no dry-spell or crop-window validation is reported, and infinitesimal-pulse behavior still requires testing. |
| ACE2-SOM, Clark et al. (2025), https://doi.org/10.1029/2024JH000575 | Stable 1-degree, 6-hourly learned atmosphere coupled to a slab ocean and trained across equilibrium CO2 levels; reproduces precipitation means and very high precipitation quantiles in held-out CO2 climates. | High-complexity daily benchmark for whether a learned dynamical emulator changes crop-feature results relative to statistical methods. | Idealized equilibrium training does not establish accuracy for transient FAIR trajectories or a small marginal pulse; it emulates its parent climate model rather than the multi-model distribution. |
| Score-based impact-variable emulator, Bouabid et al. (2026), https://doi.org/10.1029/2025MS005558 | Joint probabilistic monthly fields of temperature, precipitation, humidity, and wind conditioned on warming, evaluated across three ESMs; public code. | Multivariate monthly benchmark and uncertainty architecture. | Authors explicitly leave daily resolution for future work; precipitation tail biases and some seasonal-regime failures matter for crops. |
| MESMER-M-TP, Schöngart et al. (2024), https://doi.org/10.5194/gmd-17-8283-2024 | ESM-specific global land monthly precipitation fields conditional on monthly temperature; gamma GLM plus spatially correlated residual variability; coupled GMT-to-temperature-to-precipitation chain validated across CMIP6 models. Code and exact paper release are public. | Leading monthly mean/seasonality benchmark and candidate monthly backbone. | 2.5-degree monthly output does not identify daily wet/dry runs, within-month timing, Rx1day, or Rx5day. |
| PREMU, Liu et al. (2023), https://doi.org/10.5194/gmd-16-1277-2023 | ESM-specific gridded monthly precipitation derived from global and spatial temperature modes; calibrated across CMIP6 scenarios; public MATLAB/Zenodo code. | Independent monthly pattern benchmark and sensitivity to emulator form. | Deterministic unexplained variance treatment and monthly resolution are insufficient for crop dry spells and extremes. |
| STITCHES, Tebaldi et al. (2022), https://doi.org/10.5194/esd-13-1557-2022 | Recombines decade-long windows from existing ESM simulations to construct novel GSAT trajectories; can recover multivariate gridded output at daily resolution when archived. Public software/documentation. | Strong daily, multivariate benchmark that preserves actual within-window weather sequences and temperature--precipitation coherence. | Discrete block selection is not naturally differentiable for a very small SCC pulse; performance depends on archive coverage, and accumulations longer than a block are a stated limitation. |
| Pattern-scaled Markov--gamma generator, Kemsley et al. (2024), https://doi.org/10.1002/joc.8320 | Scales wet/dry transition probabilities and wet-day gamma amount parameters with GMST to generate daily precipitation under unsimulated warming levels. | Leading published basis for wet-day frequency, dry-spell persistence, rainfall intensity, and crop-window daily sequences. | First-order two-state persistence and gamma wet-day amounts may miss long drought memory and extreme tails; spatial coherence requires an additional treatment. |
| MESMER-X Rx1day, Pierini et al. (2026), https://doi.org/10.1088/1748-9326/ae5fad | Fast spatially explicit probabilistic global Rx1day emulation along custom global-warming trajectories; code archived at https://doi.org/10.5281/zenodo.19095277. | Independent heavy-rainfall-tail module or validation target. | Emulates Rx1day, not full daily sequences, crop timing, Rx5day, or dry spells. |
| fldgen v2.0, Snyder et al. (2019), https://doi.org/10.1371/journal.pone.0223542 | Joint annual gridded temperature--precipitation realizations with internal variability and space/time/cross-variable covariance. | Annual covariance and uncertainty benchmark. | Annual resolution cannot support within-season agricultural timing. |
| Global-WGEN, Sommer and Kaplan (2017), https://doi.org/10.5194/gmd-10-3771-2017 | Globally calibrated stochastic generator of daily precipitation, minimum/maximum temperature, cloud, and wind from monthly inputs; intended for crop, ecosystem, and hydrology models. | Transparent global daily disaggregation benchmark and fallback implementation. | Does not emulate the forced monthly climate response and lacks spatially autocorrelated multipoint precipitation. |
| RIME-X v1.0, Schwind et al. (2026), https://doi.org/10.5194/gmd-19-6797-2026; exact paper archive https://doi.org/10.5281/zenodo.21061984 | Links simple-climate-model warming distributions to gridded or regional CMIP/ISIMIP climate and impact indicators through 0.1 K warming-level conditional distributions, 101 quantiles, and linear interpolation; includes held-out-scenario validation. | Closest published direct indicator-response benchmark for daily-derived crop features; its version-pinned GIVE contract and synthetic pulse smoke are in `RIMEX_FEATURE_RESPONSE_BENCHMARK.md`. The preregistered GFDL/SSP1-2.6 2031--2060 pilot now supplies eight valid centered outputs. | The bounded mechanics pass only one ESM, one scenario, one crop, one irrigation regime, and two latitude rows. Other ESMs/scenarios and a validated joint-dependence design remain absent. Published quantile maps are univariate. Real fitting and FAIR evaluation remain closed. |

## Closest integrated crop-model precedent

OSCAR-crop v1.0 (Liu et al., 2026,
https://doi.org/10.5194/gmd-19-5857-2026) is the closest published integrated
assessment precedent. It maps global climate to subnational crop yields for
maize, two rice seasons, soybean, and spring/winter wheat, distinguishes
rainfed and fully irrigated crops, and represents CO2, growing-season
temperature, growing-season precipitation, and nitrogen. It is calibrated to
eight GGCMs driven by five CMIP6 ESMs and has public code and data at
https://github.com/Xinrui-Rea/OSCAR-crop and a frozen archive at
https://doi.org/10.5281/zenodo.17228924.

It is an essential benchmark, not a substitute for the present estimand. Its
climate response uses annual/regional and growing-season aggregates; the
authors state that extreme-weather impacts are not represented and that the
model is intended for multi-year trends. Our defensible contribution must
therefore be demonstrated relative to an OSCAR-crop-style aggregate-water
benchmark: adding daily timing, stage exposure, dry spells, heavy rain,
compound heat--moisture behavior, empirical historical validation, and an
explicit agricultural welfare replacement inside GIVE.

## Barnes, Davenport, and Diffenbaugh evidence

- Trok, Barnes, Davenport, and Diffenbaugh (2024),
  https://doi.org/10.1126/sciadv.adl3242, train climate-model CNNs to generate
  dynamically consistent counterfactual extreme events across GMT levels.
  Their main application is heat, but the supporting analysis applies the
  method to a Pacific Northwest extreme-precipitation event. This establishes
  a relevant counterfactual architecture; it is not a global continuous daily
  precipitation emulator for agricultural SCC draws.
- Davenport and Diffenbaugh (2021),
  https://doi.org/10.1029/2021GL093787, use an interpretable CNN to identify
  large-scale circulation patterns associated with Midwest extreme
  precipitation and separate changes in pattern frequency from changes in
  rainfall intensity. This motivates circulation-aware validation and helps
  diagnose failures of GMT-only scaling, but it does not generate global
  precipitation trajectories.
- Barnes and collaborators' ACE/ACE2 work provides learned global atmospheric
  simulators with explicit precipitation-fidelity evaluation. These are
  important high-complexity benchmarks, not the first-choice SCC component:
  their target atmospheric configurations, conditioning, resolution,
  computational burden, and out-of-distribution forcing behavior require a
  separate validation program.
- Ham et al. (2023), https://doi.org/10.1038/s41586-023-06474-x, detect an
  anthropogenic fingerprint in the distribution and variability of daily
  precipitation using deep learning. This is evidence that distributional
  change contains a forced signal and is a useful validation concept, but the
  model is a detector rather than a trajectory generator.

## Fallback and benchmark implementation strategy

The chain below was superseded as the primary route on 25 August 2026. Use it
only as a robustness path or if the direct ISIMIP3b crop-feature response fails
the predeclared support, holdout, identity, or pulse-convergence gates in
`PAIRED_CLIMATE_FEATURE_DRIVER.md`.

### Published-method fallback chain

1. Drive a published spatial temperature emulator with matched GIVE/FAIR
   baseline and pulse GMT trajectories, preserving a common model/member draw.
2. Use MESMER-M-TP as the monthly precipitation backbone within this fallback.
3. Adapt the Kemsley et al. pattern-scaled Markov--gamma method to create daily
   precipitation conditional on the emulated monthly field, then calculate
   crop-calendar totals, window shares, wet days, consecutive dry days, Rx1day,
   and Rx5day from daily sequences.
4. Benchmark the heavy-rainfall tail independently against MESMER-X Rx1day.
5. Compare generated daily crop features against direct ISIMIP/CMIP daily
   output and STITCHES, holding out entire ESMs and scenarios.

Before finalizing that chain, evaluate the Huang et al. RIG framework. It
supersedes a custom daily disaggregator if code and trained weights become
available and it passes the same crop-feature and pulse-convergence gates.
The current paper validates precipitation distributions, spatial spectra,
lag-1 persistence, temperature--precipitation cross-correlation, and regional
extreme-event return periods, but does not report crop-calendar totals,
wet-day frequency, CDD, Rx5day, or stage-specific compound-event fidelity.
Current reported generation cost is about 7,665 seconds per global year at
0.25 degrees, which would also make full SCC Monte Carlo use expensive without
surrogating crop features or accelerating inference. ACE2-SOM is a
high-complexity robustness benchmark, not the default, unless its transient
forcing response can be validated for the FAIR paths used by GIVE.

The adaptation must constrain monthly generated amounts to the monthly
backbone, retain joint temperature--precipitation draws, and add a documented
spatial dependence mechanism. Any change to published algorithms is named and
ablation-tested.

### Alternatives and escalation

- Use STITCHES as the primary daily approach if common-random-number
  baseline/pulse construction is sufficiently smooth and daily archive
  coverage passes the crop-feature tests.
- Use a diffusion daily disaggregator only as a robustness model until its
  peer-reviewed status, code, training domain, and tail/persistence behavior
  clear the same validation gates.
- Train a new ML climate emulator only if these published systems fail
  predeclared crop-feature validation. The failure and required new capability
  must be documented before model development begins.

## Validation gates for GIVE use

- Held-out ESM and held-out scenario performance, never random year splits
  alone.
- Crop/month-specific bias in totals, wet-day frequency, CDD, Rx1day, Rx5day,
  and early/middle/late precipitation shares.
- Spatial covariance and synchronized breadbasket dry/wet events.
- Temperature--precipitation and drought-index covariance.
- Smooth, numerically stable pulse-minus-baseline responses as pulse size is
  varied and reduced.
- Emulator uncertainty propagated as a climate-model layer, not absorbed into
  crop-response coefficient uncertainty.
- Direct daily climate calculations remain the reference; no emulator-derived
  SCC is released if feature errors are material relative to the marginal
  pulse signal.

## Novelty statement that is currently supportable

Published work already covers precipitation pattern scaling, probabilistic
monthly fields, global daily weather generation, high-frequency learned
atmospheric emulation, regional climate indicators for simple climate models,
and aggregate precipitation within a compact crop emulator. The paper must
not claim any of those pieces as new. Subject to completion of the empirical
and SCC results, the contribution is the validated combination of (i)
crop-calendar and stage-specific daily precipitation distributions, (ii)
observationally estimated crop responses separated from heat, CO2, irrigation,
and adaptation, and (iii) matched marginal-emissions welfare accounting in
GIVE.

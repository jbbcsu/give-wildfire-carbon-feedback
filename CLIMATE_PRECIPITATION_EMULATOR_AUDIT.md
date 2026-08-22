# Literature audit: climate-to-precipitation emulation

Updated: 2026-08-22

## Decision

Do **not** develop a free-standing precipitation emulator from scratch. Several
peer-reviewed, open or archived frameworks already emulate spatial
precipitation along novel warming trajectories. The project contribution
should be a validated adaptation of published methods to crop calendars and a
paired GIVE/FAIR marginal-emissions pulse, not a claim that climate-to-rainfall
emulation is new.

No identified publication alone provides all required outputs: globally
coherent crop-window totals, daily wet/dry persistence, heavy-rainfall tails,
joint temperature--precipitation dependence, and a differentiable mapping for
matched baseline/pulse SCC draws. This remaining gap is an integration and
validation problem.

## Directly relevant systems

| System | Published capability | Use here | Material limitation |
|---|---|---|---|
| MESMER-M-TP, Schöngart et al. (2024), https://doi.org/10.5194/gmd-17-8283-2024 | ESM-specific global land monthly precipitation fields conditional on monthly temperature; gamma GLM plus spatially correlated residual variability; coupled GMT-to-temperature-to-precipitation chain validated across CMIP6 models. Code and exact paper release are public. | Leading monthly mean/seasonality benchmark and candidate monthly backbone. | 2.5-degree monthly output does not identify daily wet/dry runs, within-month timing, Rx1day, or Rx5day. |
| PREMU, Liu et al. (2023), https://doi.org/10.5194/gmd-16-1277-2023 | ESM-specific gridded monthly precipitation derived from global and spatial temperature modes; calibrated across CMIP6 scenarios; public MATLAB/Zenodo code. | Independent monthly pattern benchmark and sensitivity to emulator form. | Deterministic unexplained variance treatment and monthly resolution are insufficient for crop dry spells and extremes. |
| STITCHES, Tebaldi et al. (2022), https://doi.org/10.5194/esd-13-1557-2022 | Recombines decade-long windows from existing ESM simulations to construct novel GSAT trajectories; can recover multivariate gridded output at daily resolution when archived. Public software/documentation. | Strong daily, multivariate benchmark that preserves actual within-window weather sequences and temperature--precipitation coherence. | Discrete block selection is not naturally differentiable for a very small SCC pulse; performance depends on archive coverage, and accumulations longer than a block are a stated limitation. |
| Pattern-scaled Markov--gamma generator, Kemsley et al. (2024), https://doi.org/10.1002/joc.8320 | Scales wet/dry transition probabilities and wet-day gamma amount parameters with GMST to generate daily precipitation under unsimulated warming levels. | Leading published basis for wet-day frequency, dry-spell persistence, rainfall intensity, and crop-window daily sequences. | First-order two-state persistence and gamma wet-day amounts may miss long drought memory and extreme tails; spatial coherence requires an additional treatment. |
| MESMER-X Rx1day, Pierini et al. (2026), https://doi.org/10.1088/1748-9326/ae5fad | Fast spatially explicit probabilistic global Rx1day emulation along custom global-warming trajectories; code archived at https://doi.org/10.5281/zenodo.19095277. | Independent heavy-rainfall-tail module or validation target. | Emulates Rx1day, not full daily sequences, crop timing, Rx5day, or dry spells. |
| fldgen v2.0, Snyder et al. (2019), https://doi.org/10.1371/journal.pone.0223542 | Joint annual gridded temperature--precipitation realizations with internal variability and space/time/cross-variable covariance. | Annual covariance and uncertainty benchmark. | Annual resolution cannot support within-season agricultural timing. |

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

## Revised implementation strategy

### Primary published-method chain

1. Drive a published spatial temperature emulator with matched GIVE/FAIR
   baseline and pulse GMT trajectories, preserving a common model/member draw.
2. Use MESMER-M-TP as the primary monthly precipitation backbone.
3. Adapt the Kemsley et al. pattern-scaled Markov--gamma method to create daily
   precipitation conditional on the emulated monthly field, then calculate
   crop-calendar totals, window shares, wet days, consecutive dry days, Rx1day,
   and Rx5day from daily sequences.
4. Benchmark the heavy-rainfall tail independently against MESMER-X Rx1day.
5. Compare generated daily crop features against direct ISIMIP/CMIP daily
   output and STITCHES, holding out entire ESMs and scenarios.

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

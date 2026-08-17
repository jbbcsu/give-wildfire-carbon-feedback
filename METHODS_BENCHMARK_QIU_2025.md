# Methodological benchmark: Qiu et al. (2025)

Qiu et al., *Wildfire smoke exposure and mortality burden in the USA under
climate change*, Nature, doi:10.1038/s41586-025-09611-w, provides a useful
structural benchmark for this project. It is not a source of agricultural
damage coefficients and should not be copied mechanically across sectors.

## Transferable design principles

1. **Estimate a linked causal chain.** Separate the climate-to-hazard and
   hazard-to-damage links, then carry uncertainty through the full chain. Here:
   CO2 forcing -> daily climate -> crop-season precipitation-pattern metrics ->
   crop yield -> agricultural welfare -> SCC.
2. **Use an ensemble, not a single preferred algorithm.** Compare a
   transparent fixed-effects/GAM primary estimator with penalized regression,
   tree-based models, and a constrained sequence model only where it improves
   held-out performance. Model class is an uncertainty dimension.
3. **Test temporal and spatial resolution.** Compare crop-grid, agro-climatic
   region, and welfare-region pooling; compare seasonal-total, crop-window,
   and daily-sequence feature representations. Retain only resolutions that
   meet pre-specified held-out criteria.
4. **Use nested out-of-sample selection and future-relevant extremes.** Select
   hyperparameters inside training folds, evaluate blocked spatial and
   temporal folds outside them, and separately report dry-spell and
   heavy-rainfall-tail performance. Do not choose a model on in-sample fit.
5. **Retain near-best models.** Pre-specify a performance tolerance and test
   it in sensitivity analysis; propagate retained models to SCC draws rather
   than treating a one-model winner as certain.
6. **Propagate climate-model uncertainty.** Calculate every daily
   crop-calendar metric separately for each bias-adjusted GCM/member and
   scenario/pulse path. Do not average daily climate before calculating CDD,
   wet days, stage shares, or Rx metrics.

## Necessary adaptations for an SCC agriculture application

- The historical ISIMIP3a panel identifies crop sensitivity to realized daily
  weather. It does **not** identify the marginal climate effect of one tonne
  of CO2. The latter must use matched baseline/pulse climate paths (or a
  validated climate-pattern-scaling emulator) before the crop response is
  evaluated.
- The primary response retains a joint temperature--precipitation form. An
  ML model is a benchmark/emulator, not a stand-alone causal claim.
- Quantity and distribution are evaluated jointly, then attributed using
  counterfactual feature substitutions: change seasonal total holding shape
  fixed; change normalized timing/wet-day/extreme structure holding total
  fixed; report the interaction separately.
- Crop calendars, land-use/harvested-area weights, CO2 fertilization, and
  adaptation must be versioned inputs. Do not let an empirical year effect be
  added to a separate CO2 or adaptation term.
- Qiu et al.'s specific model-selection threshold, regions, outcome, and
  scenario calculations are not imported. This project will pre-specify and
  sensitivity-test its own choices and needs marginal SCC pulse accounting,
  rather than a comparison among discrete scenario decades.

## Immediate implementation changes

The repository already has deterministic spatial/time/extreme labels. The
next empirical specification will add normalized stage precipitation shares
and concentration metrics alongside seasonal totals, then benchmark the
fixed-effects response against regularized and nonlinear alternatives in
nested blocked validation. GCM/member-level feature paths and retained-model
draws will feed the matched SCC baseline/pulse interface.

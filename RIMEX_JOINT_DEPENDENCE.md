# Preregistered RIME-X joint-dependence treatment

Status: outcome-blind contract and synthetic mechanics only. Real dependence
fitting, FAIR feature response, crop response, damage, welfare, and SCC use are
closed.

RIME-X supplies univariate warming-level conditional quantiles. The registered
extension uses ECC-Q empirical-copula coupling (Schefzik, Thorarinsdottir, and
Gneiting, 2013, https://doi.org/10.1214/13-STS443), closely related to the
Schaake shuffle (Clark et al., 2004,
https://doi.org/10.1175/1525-7541(2004)005%3C0243:TSSAMF%3E2.0.CO%3B2). It
reorders separately mapped marginal quantiles using complete climate-model
rank templates. It neither draws features independently nor imposes one
comonotonic rank on every feature.

One template is an indivisible ESM--member--scenario--center-year field across
all included grid cells, crops, irrigation regimes, stages, and transformed
features. Baseline and pulse paths reuse the exact same template identities,
tie order, and marginal probability grid. Whole-ESM and whole-scenario folds
exclude all held-out templates before selection.

The coupling operates on physical coordinates: log seasonal rain; bounded
wet-day, dry-spell, Rx5/total, and Rx1/Rx5 fractions; temperature; and two
additive-log-ratio coordinates for the three stage-rain shares. Timing centroid
and concentration are reconstructed from the coupled composition, not sampled
independently. This enforces `Rx1 <= Rx5 <= total` and a unit-sum stage
composition. Nonpositive centered total or Rx5 support fails closed.

The production minimum is 51 distinct training templates, matching 51 joint
draws. The current bounded contiguous pilot has only eight templates, one ESM,
one scenario, one crop/regime, and two latitude rows. It can validate mechanics
but cannot fit or promote real dependence. Heat extremes, drought, and
longer-duration rainfall/drought features also remain required extensions.

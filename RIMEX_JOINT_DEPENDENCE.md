# Preregistered RIME-X joint-dependence treatment

Status: outcome-blind contract, synthetic mechanics, and a failed represented-
template stability diagnostic. Real dependence fitting, FAIR feature response,
crop response, damage, welfare, and SCC use are closed.

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
draws. The original bounded contiguous pilot has only eight templates, one
ESM, one scenario, one crop/regime, and two latitude rows. It validates
mechanics but cannot fit or promote real dependence.

A later outcome-blind diagnostic locks 88 completed multicrop/calendar
templates before evaluation. For every ESM--scenario--center-year template it
derives the eight linked physical coordinates over all 7,676 registered
crop-calendar cells and records the within-template Spearman matrix. It then
compares training and held-out median matrices for each represented whole-ESM
and whole-scenario exclusion. The fixed pass rule requires mean absolute
correlation difference at most 0.05, maximum absolute difference at most 0.15,
and no sign reversal for a pair whose absolute training median is at least
0.20.

Six of seven represented exclusions pass. GFDL-ESM4, IPSL-CM6A-LR,
MPI-ESM1-2-HR, and all three SSP exclusions remain within both magnitude gates
with no strong-pair sign reversals. MRI-ESM2-0 fails because the held-out versus
training median correlation for wet frequency and Rx1 conditional on Rx5
differs by 0.192318. Its mean absolute difference is 0.043330 and no strong
pair changes sign, but the preregistered maximum gate controls. The run reads
264 derived Parquet files sequentially; maximum observed peak RSS across two
deterministic runs is 187,662,336 bytes.

No threshold is changed after this result. The balanced matrix is also still
missing MRI SSP5-8.5 and all three UKESM cells. Therefore this is adverse
structural stability evidence, not an ECC-Q or RIME-X marginal fit, and no
joint-dependence or downstream promotion gate opens. Heat extremes, drought,
and longer-duration rainfall/drought features remain required extensions.

## Locked MRI failure decomposition

Before reading further outputs, a follow-up contract fixed the failed
wet-frequency--Rx1-given-Rx5 pair, the unchanged 0.15 maximum-difference gate,
and scenario-matched, scenario-specific, center-year, and crop/regime
summaries. The primary comparison restricts MRI and the other three ESMs to
their shared SSP1-2.6 and SSP3-7.0 templates. That restriction reduces the
absolute median-correlation difference from 0.192318 to 0.173654, so the
missing MRI SSP5-8.5 cell is not sufficient to explain the locked failure.
Separate differences are 0.163224 for SSP1-2.6 and 0.204990 for SSP3-7.0, and
all eight center-year comparisons remain above 0.15.

The same checksum-bound pass computes one focal correlation for each complete
crop/regime/ESM/scenario/center-year field. Ten of twelve scenario-matched
crop/regime differences exceed 0.15. Both winter-wheat calendar cells are
exceptions, at 0.070128 for the irrigated calendar and 0.084917 for the
rainfed calendar; the maximum is 0.239124 for either second-season-rice
calendar. This heterogeneity is descriptive. The evaluator reads 264 derived
Parquet files sequentially, remained below 174 MiB RSS across verification
runs, and performs no fit or tolerance change. The balanced matrix is still
incomplete and every downstream gate remains closed.

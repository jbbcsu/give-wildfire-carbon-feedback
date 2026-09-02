# Literature-constrained RIME-X feature-response benchmark

Status: preregistered engineering benchmark; real fit, FAIR feature response,
crop response, damage, welfare, and SCC use are closed.

## Selection

After the two project-specific direct response forms failed their locked
whole-ESM/whole-scenario criteria, the next step is published-method reuse,
not outcome-adaptive tuning. RIME-X v1.0 (Schwind et al., 2026,
https://doi.org/10.5194/gmd-19-6797-2026) is the closest published direct
ISIMIP indicator-response framework. It constructs distributions of regional
or grid-cell indicators conditional on global mean temperature, using 0.1 K
warming-level increments and 101 quantiles, and linearly interpolates the
conditional quantiles onto simple-climate-model temperature paths. Its exact
paper code/data archive is https://doi.org/10.5281/zenodo.21061984; the
software identifies itself as v1.0.0.

This choice does not replace the approved direct ISIMIP3b daily-feature route.
Daily precipitation and temperature are still reduced first to the exact crop
features used by agriculture. MESMER-M-TP plus a published daily generator
remains the fallback only.

## Why the real fit remains closed

The published RIME-X application smooths indicators with a centered 21-year
running mean before constructing warming-level conditional distributions.
The bounded GIVE training artifact contains only 2012--2014, 2042--2049, and
2092--2099. Joining across either gap would invent temporal adjacency. No real
RIME-X crop-feature map is therefore fit from the current artifact.

RIME-X's published quantile maps are univariate. Agriculture needs coherent
joint draws of rainfall quantity, stage timing, wet days, dry spells, Rx1day,
Rx5day, heat, and drought. Independent quantile draws break dependence, while
reusing one rank for every feature imposes unvalidated comonotonic dependence.
Neither substitution is authorized. A real benchmark requires contiguous
daily-derived feature windows plus a separately preregistered and validated
joint-dependence treatment.

The first outcome-blind contiguous-support repair in
`RIMEX_CONTIGUOUS_PILOT.md` now passes bounded mechanics. One
GFDL-ESM4/SSP1-2.6 `pr`/`tas` realization supplies every daily year from
2031--2060, all 28 crop-feature years, and exactly eight valid centered
21-year outputs for 2042--2049. This does not weaken the multi-ESM,
multi-scenario, multi-crop, dependence, or pulse gates.

## Bounded engineering smoke

The contract in
`config/isimip3b_rimex_feature_response_benchmark_v1.toml` pins the article,
exact Zenodo revision, reviewed repository head, published grid choices,
current training hashes, and closed gates. The independently written validator
implements only two-axis linear interpolation for a synthetic map. It verifies
within-feature common random numbers, separate support flags, exact zero-pulse
and pre-divergence identity, rejection of extrapolation, and convergence over
three decreasing positive pulse sizes.

Synthetic success is a software-mechanics result only. Before any real
promotion, the method must pass exact whole-ESM and whole-scenario holdouts,
multi-crop and rainfed/irrigated validation, actual GIVE/FAIR common-random-
number pairing, joint-feature dependence, support, and pulse gates. No
empirical coefficient or SCC input is produced here.

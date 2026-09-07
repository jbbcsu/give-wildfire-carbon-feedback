# Country-specific annual controls attenuate global moisture associations

September 7, 2026. Exploratory historical associations, not causal responses,
future climate impacts, production-weighted global effects or SCC estimates.

## Main result

On exactly the same mapped sample, country-by-year controls reduce the maize
rainfall-index contrast from 0.574% to 0.367%. The soybean quantity contrast
drops from 0.381% to 0.014%, with a conditional interval spanning zero.
Soybean drought contrasts also span zero. Positive partial timing associations
remain, but do not reverse the existing small/uncertain out-of-sample evidence.
This is a sensitivity of historical associations, not validation of a model
for climate-change attribution.

Country-label-clustered normal CR1 intervals are shown below. All 16 fits
also have a 20-degree-block covariance sensitivity in the machine-readable
output. Point contrasts are invariant to clustering. These intervals are
conditional and do not account for specification search or all dependence.

| Model and partial contrast | Maize, global-year controls | Maize, country-year controls | Soybean, global-year controls | Soybean, country-year controls |
|---|---:|---:|---:|---:|
| Quantity: +0.1 weighted log-rain index | 0.574 [0.265, 0.883] | 0.367 [0.135, 0.600] | 0.381 [-0.237, 1.002] | 0.014 [-0.543, 0.574] |
| Quantity + distribution: same rain-index shift | 0.663 [0.337, 0.991] | 0.424 [0.190, 0.659] | 0.659 [-0.026, 1.348] | 0.219 [-0.390, 0.831] |
| Quantity + distribution: 0.1 share from stage 3 to stage 2 | 1.051 [0.550, 1.553] | 0.569 [0.156, 0.985] | 1.314 [0.528, 2.106] | 1.075 [0.266, 1.890] |
| Seasonal scPDSI: +1 index unit | 1.241 [0.546, 1.942] | 0.971 [0.301, 1.646] | 0.612 [-0.020, 1.248] | 0.222 [-0.199, 0.645] |
| Stage scPDSI: +1 unit in all stages | 1.221 [0.522, 1.926] | 1.008 [0.351, 1.670] | 0.562 [-0.154, 1.284] | 0.163 [-0.257, 0.586] |

Values are 100*(exp(fitted log-yield contrast)-1), not changes in arithmetic
mean yield. The rain index averages log(1+rainfall/mm) across regimes using
fixed MIRCA shares; +0.1 is not exactly 10% more rainfall or +100 mm. Timing
is a formal held-fixed partial contrast, not necessarily a physically
realizable daily-rain perturbation. The moisture models are alternatives;
their contrasts must not be added.

For comparison, the country-year quantity intervals with 20-degree blocks
are [0.129, 0.606] for maize and [-0.376, 0.406] for soybean. Seasonal scPDSI
intervals are [0.135, 1.814] and [-0.246, 0.693], respectively. Both clustering
schemes support the same qualitative description; neither is exact inference.

## Mapping and sample

The retained MapSPAM circa-2000 maize/soy union contains 601,130 five-minute
cells. Its country codes were rechecked against hash-verified retained NGA
and UN sources. Aggregating coordinate indices gives 28,340 half-degree
cells: 26,444 have a single country label, and 1,896 remain ambiguous. The
singleton footprint has 149 country labels before the outcome-panel join.
No majority-country threshold or crop-specific production weighting was used.

| Training differences ending 1983–2010 | Maize | Soybean |
|---|---:|---:|
| Original common-support pairs | 404,671 | 166,870 |
| Singleton-mapped pairs retained | 352,301 (87.06%) | 157,003 (94.09%) |
| Mixed-country footprint pairs excluded | 35,764 | 7,069 |
| Footprint-absent pairs excluded | 16,606 | 2,798 |
| Retained country labels | 111 | 21 |
| Country-year intercept groups | 3,077 | 588 |
| Singleton country-year groups | 294 | 84 |
| Retained 20-degree geographic blocks | 47 | 28 |

Country labels are a modeled-crop-footprint proxy, not independent boundary
geometry or GDHY administrative source identifiers. Circa-2000 crop selection
and static labels can affect historical coverage. Singleton intercept groups
contribute zero demeaned variation; nominal country counts are not counts of
equally informative, independent clusters. In particular, soybean inference
rests on few country labels. Residual GDHY construction dependence, nonlinear
heat response, omitted local drivers, and adaptation remain unresolved.

The global-year fits here deliberately use the restricted sample, so their
change to country-year fits is not caused by changing observations. The
earlier unrestricted global-year results remain separate. Terminal 2012–2016
test outcomes are not used, and no predictive promotion decision is changed.

## Reproduction and execution

Protocol: `GLOBAL_COUNTRY_CONTROL_PROTOCOL_20260907.md`.
Run the coordinate/border tests, `scripts/build_mapspam_country_grid.py`,
the absorbed-regression tests, then `scripts/global_country_control_associations.py`.
Pass new output paths through their `--out`/`--receipt` arguments and launch
one job at a time with `scripts/run_bounded_job.py`. Exact input hashes and
code/protocol hashes are retained in:

- `data/provenance/global_country_proxy_20260907.json`;
- `data/provenance/global_country_control_associations_20260907.json`.

The generated 44,362-byte gridded crosswalk stays under ignored `data/interim`;
raw and derived gridded redistribution remains unauthorized. No downloads
or source-table edits occurred. The bundled spreadsheet runtime lacked
PyArrow, so the existing project environment supplied that missing capability.
Three coordinate/border tests and three estimator tests pass, including
agreement with an explicit dummy-variable OLS and cluster covariance.
Post-run checks confirm all 32 covariance records, exact sample accounting,
unchanged mapped observations across variants, current code/protocol hashes
and point-estimate invariance to cluster definition.

Crosswalk construction took 3.67 seconds with 128 MiB sampled RSS (512 MiB
cap). The real fits took 14.83 seconds with 622.22 MiB sampled RSS (2 GiB
cap). These are sampled process-group maxima, not kernel-enforced limits.
No subprocess remains active after completion. Results are descriptive only.

## Next distinct step

Country control is now an executed sensitivity, not a pending task. Do not
repeat these fits on the next heartbeat. Resolve the global joint-response
counterfactual and the climate-projection route using the retained feature
ensemble, keeping mean/quantity and temporal-pattern attribution distinct.
The missing published welfare supplement remains a separate document-access
decision; do not repeat the blocked download/search without new permission.

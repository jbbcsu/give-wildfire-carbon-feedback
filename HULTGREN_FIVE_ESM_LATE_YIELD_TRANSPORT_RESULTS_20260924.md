# Preliminary five-model late-century maize response transport

## Scope and claim boundary

This diagnostic transports the published Hultgren et al. (2025) maize
response over crop-calendar-aligned GFDL-ESM4, IPSL-CM6A-LR,
MPI-ESM1-2-HR, MRI-ESM2-0, and UKESM1-0-LL SSP5-8.5-minus-SSP1-2.6
weather for harvest years 2092--2100. It is a published-coefficient benchmark,
not a new causal estimate, monetary damage estimate, marginal carbon-pulse
calculation, or social cost of carbon.

All 20 ESM-by-scenario-by-irrigation-regime weather bases pass independent
selected-cell recomputation from raw daily ISIMIP3b precipitation, Tmin, and
Tmax. Calendars, crop area, moderators, income mapping, response coefficients,
and support restrictions are held fixed across ESMs. Exact source identities,
hashes, validations, and recoverable raw-file eviction records are retained.

## Physical contrasts

Fixed-area, area-year-weighted SSP5-8.5-minus-SSP1-2.6 differences are:

| ESM | Season precipitation (mm) | Monthly concentration | GDD 8--31 C | KDD above 31 C |
|---|---:|---:|---:|---:|
| GFDL-ESM4 | -63.66 | +0.01267 | +454.39 | +129.84 |
| IPSL-CM6A-LR | +14.23 | +0.00418 | +693.27 | +275.99 |
| MPI-ESM1-2-HR | +12.83 | +0.00903 | +509.35 | +116.62 |
| MRI-ESM2-0 | +10.46 | +0.00077 | +453.29 | +126.74 |
| UKESM1-0-LL | +19.80 | +0.00450 | +609.02 | +337.66 |

The season-total sign differs across ESMs. These are named, single-realization
scenario contrasts, not probabilities.

## Fixed-practice yield-response benchmark

| Support | Component | GFDL | IPSL | MPI | MRI | UKESM |
|---|---|---:|---:|---:|---:|---:|
| Full | Precipitation | -3.57% | -3.00% | -2.58% | -1.61% | -2.03% |
|  | Quantity path | -2.93% | -2.58% | -4.17% | -1.98% | -1.02% |
|  | Distribution residual | -0.66% | -0.43% | +1.66% | +0.38% | -1.02% |
| Author min--max | Precipitation | -3.03% | -2.48% | -2.56% | -1.93% | -3.17% |
|  | Quantity path | -2.95% | -2.23% | -4.91% | -2.70% | -1.58% |
|  | Distribution residual | -0.08% | -0.25% | +2.46% | +0.79% | -1.62% |
| Author p01--p99 | Precipitation | -2.94% | -1.58% | -2.90% | -1.18% | -2.48% |
|  | Quantity path | -2.95% | -2.09% | -5.85% | -1.84% | -0.67% |
|  | Distribution residual | +0.02% | +0.52% | +3.13% | +0.66% | -1.83% |

Every net precipitation estimate and all 15 quantity-path estimates are
negative. Quantity spans -0.67% to -5.85% across model/support combinations.
The distribution residual changes sign across ESMs and support. Its simple
five-model full-support mean is -0.02%, compared with -2.56% for net
precipitation and -2.54% for the quantity path.

The evidence-led conclusion is therefore clear but bounded: quantity is the
replicated precipitation signal in this transport; timing/distribution is
material in individual ESMs but not sign-stable or robust in the named-model
mean. This does not show biological irrelevance. The quantity/distribution
split is reference-path dependent and is not a causal attribution.

The much larger joint-climate responses are temperature-driven and exposed to
late-century KDD extrapolation. They are not headline-ready damages. The
equal-model means are descriptive, not probability weights or uncertainty
intervals. Standard errors propagate only the published coefficient
covariance.

## Adaptation sensitivities

The five-model full-support descriptive means are:

| Scenario | Net precipitation | Quantity path | Distribution residual | Joint climate |
|---|---:|---:|---:|---:|
| Fixed | -2.56% (5/5 negative) | -2.54% (5/5) | -0.02% (3/5) | -53.18% (5/5) |
| Trend | -0.89% (5/5 negative) | -1.19% (4/5) | +0.91% (0/5 negative) | -42.98% (5/5) |
| Upper | +1.38% (0/5 negative) | +0.65% (2/5) | +2.17% (0/5 negative) | -25.83% (5/5) |

Trend and upper attenuate only negative cell responses while leaving modeled
benefits unchanged. Their sign reversals therefore describe the imposed
loss-only rule interacting with spatial heterogeneity; they are not evidence
that adaptation creates rainfall benefits. Components are evaluated and
attenuated separately, so adapted component means are not additive.

Fixed, trend, and upper adaptation scenarios remain in every model record.
Other crops, value weights, agricultural welfare mapping, improved
moderators, and matched GIVE marginal-pulse evaluation remain required before
monetary damage or SCC claims.

## Fixed physical-production weighting sensitivity

MapSPAM 2000 total maize production provides a separate fixed spatial weight.
It covers 98.35% of the source's production on eligible response cells and
98.03% after income matching. Within-cell rainfed/irrigated weather mixing
continues to use MIRCA hectares; only the final cell-response aggregation is
changed. This prevents a physical production weight from being mistaken for a
crop-value or welfare weight.

| Component | GFDL | IPSL | MPI | MRI | UKESM | Equal-model mean log response, as % |
|---|---:|---:|---:|---:|---:|---:|
| Net precipitation | -3.77% | -3.07% | -1.87% | -0.55% | -0.38% | -1.94% |
| Quantity path | -2.45% | -2.27% | -2.11% | -0.50% | -0.16% | -1.50% |
| Distribution residual | -1.36% | -0.82% | +0.25% | -0.05% | -0.22% | -0.44% |

All five net and quantity effects remain negative. Production weighting makes
the distribution residual negative in four models rather than three under
area weighting, but it still reverses in MPI. The central hierarchy therefore
does not change: quantity is the sign-stable component, while distribution is
a material sensitivity that cannot be assumed to have one global sign.

The fixed/trend/upper equal-model net precipitation summaries are -1.94%,
-0.72%, and +0.94%. As in the area-weighted results, the latter sign reversal
is generated by the imposed rule that attenuates losses but leaves modeled
benefits unchanged; it is not evidence that adaptation creates benefits.

The physical-production records and independent arithmetic validation are
`data/provenance/hultgren_five_esm_production_weighted_summary_20260924.json`
and `data/provenance/hultgren_five_esm_production_weighted_validation_20260924.json`.
They remain scenario-response sensitivities, not monetary damages or SCC.

## Conditional baseline-value sensitivity and monetization gate

The NGA/UN crosswalk resolves legacy MapSPAM country codes, and 119 matched
countries with 1999--2001 FAOSTAT constant-dollar maize gross production value
cover 98.05% of MapSPAM maize production. Allocating each national value to
cells in proportion to fixed MapSPAM production yields the following full-
support mean-log response summaries:

| Component | GFDL | IPSL | MPI | MRI | UKESM | Equal-model mean log response, as % |
|---|---:|---:|---:|---:|---:|---:|
| Net precipitation | -3.07% | -3.50% | -1.56% | -1.54% | -2.23% | -2.38% |
| Quantity path | -2.23% | -2.88% | -2.11% | -1.26% | -1.18% | -1.93% |
| Distribution residual | -0.86% | -0.64% | +0.56% | -0.28% | -1.07% | -0.46% |

All net and quantity responses remain negative; distribution reverses in MPI.
This supports the same evidence hierarchy as both area and production weights.

The result does **not** pass the next monetization gate. A fixed-price gross-
output diagnostic must exponentiate each cell response before applying its
baseline value. Extreme positive cell responses then generate positive
aggregates in four of five full-support models even though every mean log
response is negative. Author moderator min--max and p01--p99 screens still
leave reversals in MPI and UKESM. These products are extrapolation diagnostics,
not agricultural benefits or damages, and are not passed to GIVE.

The defensible next step is to justify a joint weather/moderator application
domain or reproduce a published response restriction before any level-dollar
or SCC calculation. The exact 15-run summary and audit are
`data/provenance/hultgren_five_esm_three_support_conditional_value_weighted_summary_20260924.json`
and `data/provenance/hultgren_five_esm_three_support_conditional_value_weighted_validation_20260924.json`.

A post hoc joint weather-support test clarifies the source of the failure. If
both scenarios' eight weather primitives must lie within the author-sample
minimum--maximum, retained value is 80.4%--99.0% across ESMs and the cell-first
fixed-price precipitation change is negative in all five. The tighter p01--p99
screen retains only 6.3%--51.8% and reverses the mean-log sign in three models.
The minimum--maximum boundary is therefore a plausible next specification,
but choosing it changes model-specific support and requires an explicit
modeling decision before monetization.

The published paper provides a more direct sensitivity rule: projected
log-yield impacts are winsorized at the top and bottom 1% over region--GCM--
years by RCP and crop. Applying the same percentile rule to our different
cell--ESM--year precipitation responses yields bounds of -0.652/+0.510 log
points. It affects only 0.25%--1.39% of value weight and produces negative
cell-first fixed-price output changes in all five models:

| ESM | Winsorized output change | Fixed-price gross-output exposure |
|---|---:|---:|
| GFDL | -2.42% | -US$3.40 billion |
| IPSL | -2.33% | -US$3.27 billion |
| MPI | -0.61% | -US$0.85 billion |
| MRI | -0.46% | -US$0.65 billion |
| UKESM | -0.93% | -US$1.31 billion |

This is a published-style benchmark, not an exact replication: our geographic
units, five-model ensemble, scenarios, and precipitation-only impact contrast
differ. The dollar column holds prices fixed and represents gross-output
exposure, not producer/consumer welfare, a marginal carbon pulse, damage, or
SCC. It provides a defensible interim tail treatment for the next market-
welfare stage without converting the current result into an SCC claim.

## Quarantined global-market bridge

A fully anticipated, frictionless single-global-maize-market sensitivity was
run after the published-style winsorization. It crosses the three published
supply/demand elasticity pairs with two explicit yield-to-supply mappings and
the fixed, trend, and upper loss-only adaptation scenarios. Under the central
0.10/0.04 elasticity pair and horizontal-output mapping, the fixed-adaptation
damage-signed surplus changes average US$3.520, US$3.455, US$1.043, US$0.863,
and US$1.441 billion per year for GFDL, IPSL, MPI, MRI, and UKESM. The
five-model mean is US$2.064 billion in constant 2014--2016 dollars.

Across all models, elasticity pairs, and mappings, the fixed range is
US$0.220--4.034 billion. Trend adaptation has a central five-model mean of
US$0.571 billion and full range of -US$1.032--2.063 billion; upper adaptation
has a central mean of -US$1.312 billion and range of -US$2.744 to -0.209
billion. Negative damage-signed values are benefits. Because the adaptation
rules attenuate losses but not gains and omit adaptation costs, the sign
reversal is a structural bound, not evidence of net adaptation benefits.

An independent recomputation verified all 810 annual case records with zero
dollar discrepancy. The exercise is not the published country-market,
expectations, and storage model; it omits trade, other crops, and a marginal
emissions pulse. It is therefore not promoted as welfare damage or SCC and is
not passed to GIVE. Machine-readable receipts are
`data/provenance/hultgren_global_maize_market_sensitivity_20260924.json` and
`data/provenance/hultgren_global_maize_market_sensitivity_validation_20260924.json`.

The same response is also valued in 116 separate national maize markets, the
published study's central market geography. Central fixed-adaptation results
are US$5.879, US$8.407, US$3.635, US$4.794, and US$5.666 billion for GFDL,
IPSL, MPI, MRI, and UKESM; their mean is US$5.676 billion. The full fixed range
is US$1.230--15.713 billion. Trend and upper central means are US$2.837 billion
and -US$0.126 billion. The larger national-market result arises from separate
price responses to heterogeneous country shocks, not larger yield changes.
An independent audit again reproduces all 810 annual records exactly. Because
expectations, storage, trade, other crops, and the marginal pulse remain
absent, this remains a structural sensitivity rather than damage or SCC.

Machine-readable results are under `data/provenance/`, including
`hultgren_five_esm_grid_yield_transport_summary_20260924.json`.

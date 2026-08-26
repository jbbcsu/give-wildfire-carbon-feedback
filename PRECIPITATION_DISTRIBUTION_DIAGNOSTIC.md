# Precipitation-distribution predictive diagnostic

## Purpose and boundary

This version-1 diagnostic asks whether explicit within-growing-season rainfall
pattern variables improve held-out prediction of annual log-yield changes over
a seasonal-rainfall-quantity model. It is a screening exercise for maize and
soybean, not a causal response estimate or a production-model selection rule.
It cannot supply damages, response draws, or an SCC input.

Seasonal rainfall quantity is the parsimonious reference and is not assumed to
be inferior. Distribution features are retained for later production
consideration only if incremental out-of-sample value is robust and stable;
null, heterogeneous, and worse results are part of the finding. PDSI/scPDSI,
SPEI, and soil-moisture representations are evaluated in separate competing
families rather than appended to this direct-precipitation screen.

The validated 54-column source tables retain
`fit_authorized=false`. The separate contract
`gdhy_precipitation_distribution_predictive_diagnostic_v1` authorizes only
transient fitting for held-out predictions. Coefficients, intercepts, standard
errors, and test statistics are neither returned nor written. Causal
interpretation, production-model selection, response export, and SCC use are
all explicitly false.

## Frozen diagnostic comparison

Every model uses the same three stage-mean-temperature controls. The diagnostic
then compares:

1. temperature controls only;
2. temperature plus seasonal `log(1 + precipitation)` quantity;
3. quantity plus stage-based timing centroid and concentration HHI;
4. quantity plus stage wet-day occurrence and conditional wet-day intensity;
5. quantity plus stage maximum dry-spell fractions;
6. quantity plus stage Rx1day and Rx5day wet extremes; and
7. quantity plus all registered distribution sets.

The timing model uses the centroid and HHI and omits all three stage
precipitation shares. With three shares constrained to sum to one (apart from
the separately audited zero-rain case), including the shares alongside their
linear timing summary would introduce algebraic redundancy. The combined model
therefore also omits stage shares.

The current candidate builder's centroid is a **stage-index centroid**, using
the ordered-stage positions 1/6, 1/2, and 5/6. Those positions are not the
literal midpoints (0.15, 0.50, 0.85) of the 0/30/70/100 windows. For these
symmetric three windows the two centroids are affine transforms, so a linear
first-difference model with an intercept produces the same fitted values after
training-fold standardization. A production feature contract should nonetheless
carry the actual window boundaries through the allocation audit and construct
literal time coordinates from them.

The 1 mm wet-day definition and 0--30%, 30--70%, and 70--100% crop-season
windows are diagnostic quality-assurance choices only. They are not empirical
threshold selections, observed phenological stages, or production assumptions.
A production response requires literature-registered or training-only selected
definitions followed by untouched external validation.

## Leakage and identity controls

The diagnostic first-differences consecutive observed log yields within each
crop/grid cell. Its five 5-degree spatial folds are outcome-blind. The final two
years form the temporal holdout. Climate-extreme labels use the within-cell
95th percentiles of seasonal maximum consecutive dry days and Rx1day. Temporal
and extreme training pairs are purged whenever either level-yield endpoint also
appears in a test pair. Spatial folds are cell-disjoint and their endpoint
overlap is independently checked.

The executable fails closed on:

- specification-hash or lock-file drift;
- source Parquet or source allocation-audit hash drift;
- source contract, allocation order, row count, crop, or year drift;
- a wet-day threshold other than the locked 1 mm diagnostic choice;
- a stage registry other than the locked 0/30/70/100 diagnostic proxy;
- any attempt to mark the source basis fit- or SCC-authorized;
- any stage-share/timing redundancy or model-registry drift; and
- any coefficient-like field in an output or validation summary.

By default, the validation command reruns the complete diagnostic from the
hash-locked source panel and compares every reported field with the fresh
result (with only a tight cross-platform floating-point tolerance). Thus an
internally consistent but altered RMSE cannot pass merely by reconciling its
arithmetic. `--skip-source-file-verification` is a structural-review escape
hatch only and must not be used to certify empirical results.

The lock intentionally fingerprints ignored derived inputs. It does not make
those artifacts distributable and does not change the repository rule that raw
and large intermediate data remain untracked.

## Reproduction

Run the synthetic contract and failure-mode tests:

```bash
./.venv/bin/python scripts/test_precipitation_distribution_diagnostic.py
```

Run and independently validate each locked real panel:

```bash
./.venv/bin/python scripts/evaluate_precipitation_distribution_diagnostic.py \
  --crop mai \
  --out outputs/irrigation_basis/maize_mirca2000_1982_1989_distribution_diagnostic_v1.json

./.venv/bin/python scripts/validate_precipitation_distribution_diagnostic.py \
  --audit outputs/irrigation_basis/maize_mirca2000_1982_1989_distribution_diagnostic_v1.json \
  --summary-out outputs/irrigation_basis/maize_mirca2000_1982_1989_distribution_diagnostic_v1_summary.json

./.venv/bin/python scripts/evaluate_precipitation_distribution_diagnostic.py \
  --crop soy \
  --out outputs/irrigation_basis/soy_mirca2000_1982_1989_distribution_diagnostic_v1.json

./.venv/bin/python scripts/validate_precipitation_distribution_diagnostic.py \
  --audit outputs/irrigation_basis/soy_mirca2000_1982_1989_distribution_diagnostic_v1.json \
  --summary-out outputs/irrigation_basis/soy_mirca2000_1982_1989_distribution_diagnostic_v1_summary.json
```

Repeat the same diagnostic on the later 2012--2016 panels with the explicit
later-period lock:

```bash
./.venv/bin/python scripts/evaluate_precipitation_distribution_diagnostic.py \
  --crop mai \
  --lock config/precipitation_distribution_diagnostic_2012_2016.lock.toml \
  --out outputs/irrigation_basis/maize_mirca2000_2012_2016_distribution_diagnostic_v1.json

./.venv/bin/python scripts/validate_precipitation_distribution_diagnostic.py \
  --audit outputs/irrigation_basis/maize_mirca2000_2012_2016_distribution_diagnostic_v1.json \
  --lock config/precipitation_distribution_diagnostic_2012_2016.lock.toml \
  --summary-out outputs/irrigation_basis/maize_mirca2000_2012_2016_distribution_diagnostic_v1_summary.json

./.venv/bin/python scripts/evaluate_precipitation_distribution_diagnostic.py \
  --crop soy \
  --lock config/precipitation_distribution_diagnostic_2012_2016.lock.toml \
  --out outputs/irrigation_basis/soy_mirca2000_2012_2016_distribution_diagnostic_v1.json

./.venv/bin/python scripts/validate_precipitation_distribution_diagnostic.py \
  --audit outputs/irrigation_basis/soy_mirca2000_2012_2016_distribution_diagnostic_v1.json \
  --lock config/precipitation_distribution_diagnostic_2012_2016.lock.toml \
  --summary-out outputs/irrigation_basis/soy_mirca2000_2012_2016_distribution_diagnostic_v1_summary.json
```

## Early-period locked result, 1982--1989

The independent full-recomputation validator reproduces the following pooled
RMSEs. “Best distribution” is a descriptive label within the locked candidate
set; it is not a model-selection decision.

| Crop | Holdout | Temperature only | Seasonal quantity | Best distribution candidate | Best RMSE | Best minus seasonal RMSE |
|---|---|---:|---:|---|---:|---:|
| Maize | Spatial blocks | 0.296296 | 0.293487 | All distribution sets | 0.292314 | -0.001173 |
| Maize | Temporal | 0.311789 | 0.307181 | All distribution sets | 0.305890 | -0.001291 |
| Maize | High-tail stress | 0.301018 | 0.299927 | All distribution sets | 0.298545 | -0.001382 |
| Soybean | Spatial blocks | 0.225750 | 0.221850 | All distribution sets | 0.219402 | -0.002448 |
| Soybean | Temporal | 0.271999 | 0.263635 | Timing + concentration | 0.262790 | -0.000845 |
| Soybean | High-tail stress | 0.226762 | 0.222857 | All distribution sets | 0.220249 | -0.002608 |

The full combined distribution model is not uniformly better: for the soybean
temporal holdout it has RMSE 0.267185, which is 0.003549 worse than seasonal
quantity alone. Timing plus concentration improves five of the six pooled
comparisons, but is 0.000052 worse in the soybean high-tail split. Individual
fold/year signs are also heterogeneous. These are small pooled predictive
differences without paired uncertainty intervals or multiple-comparison
adjustment, so they are screening evidence only.

## Later-period locked result, 2012--2016

The same independently recomputed screen now covers 60,818 observed maize
levels (46,434 consecutive pairs) and 26,748 observed soybean levels (20,682
pairs). The table identifies the lowest-RMSE *distribution extension* in each
holdout, even where seasonal quantity or temperature alone performs better.
A negative improvement means that the extension worsens RMSE relative to
seasonal quantity.

| Crop | Holdout | Temperature only | Seasonal quantity | Lowest-RMSE distribution extension | Extension RMSE | Improvement versus seasonal quantity |
|---|---|---:|---:|---|---:|---:|
| Maize | Spatial blocks | 0.282273 | 0.281460 | Wet extremes | 0.281605 | -0.000145 |
| Maize | Temporal | 0.271440 | 0.272356 | Wet extremes | 0.273284 | -0.000928 |
| Maize | High-tail stress | 0.286105 | 0.285751 | Timing + concentration | 0.285707 | 0.000044 |
| Soybean | Spatial blocks | 0.183429 | 0.181734 | Dry spells | 0.180218 | 0.001516 |
| Soybean | Temporal | 0.214056 | 0.212356 | Timing + concentration | 0.212499 | -0.000143 |
| Soybean | High-tail stress | 0.188789 | 0.186610 | Occurrence + intensity | 0.185243 | 0.001366 |

No registered distribution family improves on seasonal quantity in all three
holdouts for either crop. In maize, every distribution extension worsens the
spatial and temporal scores; the only improvement is 0.000044 RMSE for timing
and concentration in the high-tail split. The full distribution set is worse
than seasonal quantity by 0.000818, 0.004826, and 0.002639 in the maize
spatial, temporal, and high-tail comparisons. In soybean, dry spells improve
the spatial score and occurrence/intensity improves the high-tail score, but
every distribution extension worsens the temporal score. The full set is
0.003491 worse than seasonal quantity temporally. These later-period results
do not meet the registered stability criterion for retaining a distribution
extension.

The result also contains adverse evidence beyond the within-family comparison.
For maize in the 2015--2016 temporal block, the zero-change RMSE is 0.267661;
temperature only (0.271440), seasonal quantity (0.272356), and every
distribution extension are worse. The result is retained rather than selecting
a model by period. As in the early panel, the high-tail label is not a
rare-event test: it contains 66.15% of maize pairs and 66.39% of soybean pairs
because either endpoint in a short five-year panel can trigger either CDD or
Rx1day labeling.

A separate three-model minimal-basis complete-positive-support sensitivity
retains 87.06% of maize observed levels and 91.23% of maize consecutive pairs,
and 91.07% and 94.23% for soybean. Seasonal joint temperature--quantity is
lowest-RMSE in all six crop-by-holdout comparisons in that selected balanced
sample. The seven-family distribution screen has not been rerun on that
subset. Conditioning on complete GDHY support can itself select a
nonrepresentative sample, so this is a sample-composition check rather than an
outcome repair or the primary panel.

## Interpretation limits

The 1982--1989 panels cover only eight outcome years and only maize and
soybean. The models are linear first-difference prediction benchmarks. They do
not yet include damaging heat thresholds, soil moisture, climatic water
balance, CO2 fertilization, economic adaptation, prices, or independent
welfare weights. Incremental held-out RMSE can show whether a candidate feature
set carries predictive information in this sample; it cannot identify the
causal effect of a climate-induced redistribution of rain or establish global
external validity.

GDHY is a modeled and observation-aligned gridded yield product, not direct
farm observations. In the later panel, the unexplained official 2015 support
drop affects both transitions used by the temporal holdout. Complete-support
conditioning is therefore reported alongside, but cannot validate or repair,
that temporal comparison.

Two validation labels also require narrow interpretation. The five-degree
blocks are hash-assigned across folds without a geographic buffer, so this is
blocked random cross-validation rather than leave-region-out extrapolation.
And with only eight years, the union of two within-cell 95th-percentile level
labels is necessarily much broader than a five-percent pair tail: it marks
48,667 of 102,847 maize pairs (47.32%) and 19,703 of 41,915 soybean pairs
(47.01%) because a pair is held out when either endpoint is high-tail for
either CDD or Rx1day. This is a retrospective high-tail stress split, not a
prospective estimate of rare-event performance. The pooled RMSE rankings have
no paired uncertainty intervals and must not be described as statistically
established improvements.

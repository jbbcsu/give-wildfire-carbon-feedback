# Maximum-temperature controls change moisture-model rankings

Exploratory September 5 sensitivity: 240 aggregate model/split metric rows,
120 with original controls and 120 with additional stage-average Tmax and
squared-level terms. Identical audited 20,228 first-difference observations;
rainfall and PDSI remain separate competing model families. No new data.

## Main result

Soybean rainfall-distribution promotion is **not robust** to the richer
temperature controls. Originally both soybean practices passed the existing
geographic improvement rule; neither passes with the added Tmax controls.
Neither corn practice passes under either control specification.

For non-irrigated soybeans, distribution still reduces RMSE in all three
eligible geographic tests (AR: 0.006222; KS: 0.011440; NE: 0.001702), but
the Nebraska gain is below the frozen materiality floor. This is failure
of the magnitude criterion, not a sign reversal. The distribution family
contains timing, dry spells and extremes; this is not a timing-only test.

## Later-year test: non-irrigated crops

RMSE of first differences in log yield; lower is better. These are previously
examined terminal-time splits, not new independent confirmation. PDSI is a
joint moisture-stress predictor, not an isolated precipitation response.

| Predictor family | Corn original | Corn +Tmax | Soy original | Soy +Tmax |
|---|---:|---:|---:|---:|
| Temperature controls only | .612802 | .435670 | .445779 | .315622 |
| Rainfall quantity | .516006 | .430460 | .391828 | .318341 |
| Quantity plus distribution | .455664 | .398487 | .333560 | .304585 |
| Seasonal PDSI | .466790 | .390373 | .366468 | .298782 |
| Stage/preplant PDSI | .470971 | .391427 | .356036 | .296695 |

Added controls substantially improve the controls-only model. For soybeans,
quantity alone becomes slightly worse than controls-only in this split.
PDSI families have the lowest later-year RMSE with added controls, but this
does not establish a universal geographic ranking or causal superiority.
For example, seasonal PDSI is worse than quantity in the non-irrigated corn
South Dakota geographic test. Retain all split-level results and do not select
models on this terminal comparison.

The evidence no longer supports an unqualified claim that soybean
distribution features offer robust incremental prediction across reasonable
temperature controls. Historical positive timing coefficients and this
predictive limitation can coexist. Daily heat-threshold exposure, spatial
uncertainty and drought attribution remain open. No welfare/SCC result exists.

## Reproduction and resources

Script: `us_county_validation/scripts/evaluate_moisture_tmax_sensitivity.py`;
protocol: `US_MOISTURE_TMAX_PROTOCOL_20260905.md`; verified artifact:
`data/provenance/us_moisture_tmax_sensitivity_verified_20260905.json`.
It pins retained inputs to the earlier independent audit's SHA256 values,
checks exact common keys, and constructs squared levels BEFORE differencing.
It retains original endpoint purging and training-only scaling. Threshold
outputs inherited from the evaluator are exploratory diagnostics, not an
authorization to promote the modified specification.

The verified run completed in 5.73 seconds at 235,094,016 bytes sampled
process-group RSS (224.2 MiB), under the 1 GiB monitor. A first verification
attempt stopped on a key-check dtype mismatch; the final check compares
actual ordered key values and the rerun passed. No source data changed.

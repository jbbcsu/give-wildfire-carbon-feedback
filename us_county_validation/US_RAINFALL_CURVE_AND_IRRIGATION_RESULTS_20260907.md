# Rainfall–yield curves and paired irrigation-practice differences

Completed September 7, 2026. These are exploratory **regional historical
associations**, not nationally representative U.S. estimates, causal effects
of rainfall or irrigation, climate-change damages, adaptation values or SCC.

## What the curves show

In the matched county/year sample, drier growing seasons have substantially
lower fitted non-irrigated yields, conditional on the registered controls.
The analogous irrigated associations are much smaller. Adding daily heat
controls attenuates the non-irrigated dry-weather association, especially for
corn; it does not remove it. Timing controls change these quantity curves
only modestly. This does not demonstrate robust incremental predictive value
for timing, and does not supersede the previous predictive failures/nulls.

For illustration, the table uses the quantity-only specification with 29°C
daily heat controls. All 24 original specifications are retained in the result;
this illustrative choice is not promotion of a new primary model.

| Crop and reported practice | County-years / counties / states | Median rainfall →10th percentile | Fitted yield contrast, % [pointwise95% interval] |
|---|---|---|---|
| Corn, non-irrigated | 7,013 /361 /10 | 400.7→259.5mm | -12.88 [-14.66, -11.06] |
| Corn, irrigated | 7,013 /361 /10 | 400.7→259.5mm | -0.68 [-1.62, 0.27] |
| Soybean, non-irrigated | 4,844 /255 /5 | 397.2→259.6mm | -10.18 [-12.16, -8.15] |
| Soybean, irrigated | 4,844 /255 /5 | 397.2→259.6mm | -1.01 [-1.98, -0.02] |

These finite contrasts hold the remaining regressors fixed. They are not
observed yield changes in a particular drought, a joint weather event, or
changes in unconditional expected yield. Percentages exponentiate differences
on the fitted log-yield scale; intervals condition on specification and support.
The two practices share the same selected county/year weather records, not
the same farms or fields. Do not interpret the four rows as a randomized
irrigation comparison.

For non-irrigated quantity-only corn, the median→10th-percentile contrast is
-15.82% with only mean-temperature controls, -12.88% with 29°C daily heat,
and -13.06% with 30°C daily heat. Soybean values are -11.46%, -10.18% and
-10.39%. The daily-heat variants have similar curves, but this is sensitivity
within a particular model family, not proof against omitted-driver bias.

## Support matters

Curves span each crop/practice's pooled 5th–95th rainfall percentiles, relative
to its median. Only 179/361 corn counties (49.6%) have observed rainfall ranges
containing both the pooled median and 10th percentile; 149/361 (41.3%) span
median and 90th percentile. For soybean these counts are 159/255 (62.4%) and
169/255 (66.3%). Even a pooled within-range contrast can therefore be outside
many individual counties' observed ranges. These are range diagnostics, not
joint temperature–rainfall support checks or dense-support guarantees. No
observations were trimmed or models refitted to improve this diagnostic.

## Paired difference: uncertainty accounts for shared county/year errors

Twelve additional paired fits use log(irrigated yield) minus log(non-irrigated
yield) on the identical design. Every coefficient equals the difference of
the original practice-specific coefficients to within 3.22e-15. Covariance is
estimated from the paired residuals, not by assuming independent practice fits.
The table reports median→10th-percentile changes in the **fitted irrigated /
non-irrigated yield ratio**, in percent—not a percentage-point yield difference.

| Heat threshold | Crop | Quantity only | Quantity + timing |
|---|---|---|---|
| 29°C | Corn | 14.00 [11.51, 16.55] | 14.56 [12.08, 17.08] |
| 30°C | Corn | 14.36 [11.87, 16.90] | 14.88 [12.41, 17.41] |
| 29°C | Soybean | 10.22 [7.76, 12.73] | 10.61 [8.15, 13.13] |
| 30°C | Soybean | 10.46 [8.00, 12.97] | 10.82 [8.35, 13.34] |

This is evidence of different conditional rainfall associations by reported
practice. It is **not** irrigation's causal yield benefit: selection, soils,
management, technology and field exposure can differ. It contains no water
availability, pumping cost, adoption or adaptation-cost estimate and cannot
calibrate the GIVE `trend` or `upper` adaptation scenarios on its own.

## Figures, provenance and reproduction

Three scientifically identical-layout figures show every original form under
baseline/29°C/30°C heat controls, with common vertical limits. All were visually
inspected. They remain in ignored local outputs and are reproducible from the
tracked aggregate JSON; no raw NASS/weather rows or per-observation predictions
are exported.

- [29°C heat-control curves](../outputs/us_rainfall_curves_figures_20260907/heat_29c.png)
- [30°C heat-control curves](../outputs/us_rainfall_curves_figures_20260907/heat_30c.png)
- [Baseline curves](../outputs/us_rainfall_curves_figures_20260907/baseline.png)
- Protocols: `US_RAINFALL_CURVE_PROTOCOL_20260907.md` and
  `US_PAIRED_IRRIGATION_CONTRAST_PROTOCOL_20260907.md`.
- Code: `scripts/summarize_rainfall_response_curves.py`,
  `scripts/estimate_paired_irrigation_rainfall_contrasts.py`, and
  `scripts/render_rainfall_response_curves.py` within this directory.
- Results: `data/provenance/us_rainfall_response_curves_20260907.json` and
  `data/provenance/us_paired_irrigation_rainfall_contrasts_20260907.json`,
  relative to the project root. Complete model matrices and rainfall covariance
  blocks are saved. Both files reject causal/SCC interpretation explicitly.

Five curve and two paired-estimation synthetic tests passed. Recovering the
24 covariance blocks reproduced every original coefficient and SE exactly
(maximum difference 0). Source/config/implementation hashes and sample counts
are checked before export. The curve job took 3.13s with sampled peak RSS 232.95MiB;
the paired job took 1.78s and 248.02MiB, both under 1GiB monitors. No new data were
downloaded. Both analysis scripts require a fresh `--out` path. Run them through
`scripts/run_bounded_job.py` with one numerical thread in the existing `.venv`.
The renderer uses Python's standard library and a supplied installed Node/sharp
runtime (`--input`, `--outdir`, `--node`, `--sharp-module`); no dependency
installation is required. SVG/PNG render hashes are saved in its output folder.

Remaining limitations include regional reporting selection, weather/calendar
measurement error, unmeasured drivers, wider spatial dependence, and the
inherited conditional covariance/absorbed-fixed-effect convention. Pointwise
normal bands are not simultaneous confidence bands and do not include model
selection or climate/valuation uncertainty. These calculations advance the
U.S. evidence package, not the missing global attribution/welfare/SCC chain.

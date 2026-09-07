# Rainfall–yield associations after daily heat controls

All 24 fits completed on identical 1981–2018 regional direct-practice
samples. Original county and state-year fixed effects, both rainfall forms
and both irrigation practices are retained. Daily heat controls add stage
exceedance sums and counts, with linear/quadratic terms, at one threshold at
a time. These are exploratory historical associations, not causal estimates.

## Non-irrigated crop comparison

Fitted percentage yield contrast for +100 mm seasonal rain at the full-sample
median; county-clustered normal 95% intervals in parentheses. Corn uses the
quantity form, soybeans the quantity-plus-stage-share form solely for
comparison to earlier results, not new promotion of the soybean timing model.

| Controls | Corn | Soybeans |
|---|---:|---:|
| Original stage mean temperatures | 7.72% (6.78–8.67) | 4.46% (3.44–5.50) |
| Add daily heat above 29 C | 5.68% (4.71–6.66) | 3.82% (2.73–4.91) |
| Add daily heat above 30 C | 5.77% (4.80–6.76) | 3.90% (2.82–4.98) |

Sample sizes remain 7,013 corn county-years in 361 counties/10 states and
4,844 soybean county-years in 255 counties/5 states. Reference rainfall is
400.736 mm for corn and 397.169 mm for soybeans. Conditional intervals do not
resolve spatial dependence beyond county, omitted variables or adaptation.

For soybeans, shifting ten percentage points of total seasonal rain from
stage 3 to stage 2, holding total and included controls fixed, has a fitted
association of 4.43% (3.37–5.50) under 29 C heat controls and 4.38%
(3.32–5.44) under 30 C controls, versus 4.73% originally. This mathematical
partial contrast is not a realizable future-weather counterfactual by itself.

## Geographic influence (next step completed without waiting for another run)

Thirty omit-one-state fits plus four references also completed. With 29 C
controls, corn's quantity association ranges 4.44–6.92% and soybean's
2.46–5.41%; soybean timing ranges 3.37–5.15%. With 30 C controls the ranges
are 4.66–6.80%, 2.47–5.66% and 3.40–5.19%, respectively. These are influence
ranges, NOT confidence intervals. Kansas/Nebraska omissions define the
extremes: Kansas removal gives the lowest quantity association; Nebraska
removal gives the highest. The ordering reverses for soybean timing.

No omission reverses the point associations, but magnitude is not invariant.
This cannot substitute for geographic prediction or spatially robust inference.

## Interpretation alongside the predictive results

More complete heat controls attenuate the rain-quantity association,
especially for corn. Positive timing coefficients coexist with failure of
the predeclared uniform-geographic predictive improvement rule in the
separate moisture comparison. Predictive screening and fixed-effect
associations use different estimators/bases and answer different questions.
Neither establishes globally transferable precipitation damages.

## Reproduction

`scripts/estimate_daily_heat_rainfall_associations.py` in this directory's
script folder uses the validated heat table and original outcome receipt,
without changing their source files. A QR/triangular-solve cluster covariance
implementation reproduces original baseline coefficients/SEs within 2.0e-14.
Its synthetic numerical test matches a separate normal-equation calculation.
The 24 fitted cells retain all alternatives and bind code/input/protocol hashes
in `data/provenance/us_daily_heat_rainfall_associations_20260907.json`.
The geographic companion is `evaluate_daily_heat_state_influence.py`, with
all 34 cells in `data/provenance/us_daily_heat_state_influence_20260907.json`.

No covariance warnings occurred. The first job took 6.03 seconds at
246,677,504 bytes (235.2 MiB) sampled RSS; the geographic job took 4.19 seconds
at 255,016,960 bytes (243.2 MiB). Both ran sequentially under the approved
4 GiB ceiling with no downloads, no new daily-weather processing and tiny
aggregate outputs. These timings measure jobs, not total research work.

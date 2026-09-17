# Published-style monthly GMT–rainfall benchmark: first held-out climate results

These are **raw-CMIP6 native-grid climate-only** scores, not crop-area,
yield, damage or SCC results. The test uses the preregistered PEEPS-style
linear per-ESM/calendar-month precipitation response to the *same ESM's*
annual GMST, fitted on SSP5-8.5 2015–2080. GFDL-ESM4 and IPSL-CM6A-LR
are kept separate. The unchanged 1981–2010 monthly climatology and an
annual-quantity-only fit using the identical SSP5-8.5 training years and
GMST are the named comparators. Holdouts are the entire SSP1-2.6
2031–2060 scenario and late SSP5-8.5 2081–2100. Training, source,
physical-support rule and metrics were registered before scores were read
in `PUBLISHED_MONTHLY_GMT_RESPONSE_BENCHMARK_PROTOCOL_20260917.md`.

| ESM / holdout | Quantity-only monthly-amount RMSE (mm/month) | Monthly-pattern RMSE (mm/month) | Quantity-only share TV | Monthly-pattern share TV | Monthly-model negative cell-months | Years outside training GMST |
|---|---:|---:|---:|---:|---:|---:|
| GFDL / SSP1-2.6 2031–60 | 57.555 | 56.992 | 0.19509 | 0.19334 | 2,621 | 0/30 |
| IPSL / SSP1-2.6 2031–60 | 59.703 | 59.155 | 0.20759 | 0.20348 | 7,805 | 0/30 |
| GFDL / SSP5-8.5 2081–2100 | 64.873 | 64.431 | 0.20005 | 0.19926 | 127,856 | 19/20 |
| IPSL / SSP5-8.5 2081–2100 | 78.611 | 75.837 | 0.21701 | 0.20961 | 99,208 | 17/20 |

RMSE is computed on the native **global atmosphere grid**, weighted by
verified `areacella`; it is not restricted to cropland or land. Every
finite source cell-month contributes to amount RMSE, including physically
invalid **predictions**. Share total-variation distance (TV, 0–1) uses
one common cell-year area support where actual and all three comparator
paths have positive annual precipitation and no negative monthly amount.
That common support is 99.777%/98.680% of weighted cell-year area in
the two SSP1-2.6 tests, falling to 90.196%/82.975% in the late tests.
The unchanged-climatology monthly RMSEs are 57.754, 60.359, 66.666 and
83.956 mm/month in table order. In the first two scenario holdouts, the
monthly-pattern improvement over quantity-only is small (~0.98% and
~0.92% in monthly RMSE), and the fitted linear fields already generate
negative rain in some cells. The late time-block improvement is not a
valid extrapolation result: most years exceed the training GMT range
and negative forecasts become material (minimum predicted monthly
amounts −65.65 and −204.07 mm for GFDL and IPSL). Quantity-only also
generates negative cell-months late (192 and 11,407), so it is not an
automatically valid direct forcing alternative.

The first result is thus **not** that month-level distribution is
irrelevant. Adding month-specific responses improves native-grid
holdout point scores in both ESMs. The stronger result is that this
simple linear form, as fitted, fails the physical nonnegative-rainfall
gate and cannot yet drive GIVE. The all-grid skill comparison may differ
on fixed crop footprints and seasons; that analysis is still required.
Neither SSP contrasts nor these regressions cleanly isolate GMT as the
only causal climate driver; scenario forcing histories and internal
variability remain. A nonlinear/positive-link or published probabilistic
monthly benchmark may be tested only with a frozen design and the same
holdouts, not selected opportunistically from these scores. Direct daily
ISIMIP features remain the primary reference for stage timing, dry spells,
heavy rain and compound heat–moisture behavior.

All four outputs passed source/member/calendar/hash/MD5 gates and a
separate 108-comparison 50-digit Decimal audit of year-level saved
area-weighted score aggregates (maximum scaled error 2.01e-16). The
largest sampled holdout worker RSS was 409.16 MB, below 512 MiB;
owned outputs were <0.06 MB each and free disk remained above
130 GiB. No raw climate chunk, private data, credential, yield
coefficient or SCC number was exported.

Next: transfer holdout/source predictions to the fixed MIRCA rainfed
maize crop-area and crop-calendar ledger, audit calendar-year and
cross-year season amount/month-share comparisons, and test whether
the modest all-grid monthly gain survives on crop-relevant support.
This still will not supply daily dry-spell/extreme fidelity or identify
agricultural welfare effects.

# Published PEEPS monthly rainfall on rainfed-maize centers: first screen

This is an **author-coefficient climate-input diagnostic**, not a direct
climate-model holdout, crop-year exposure, yield effect, damage, or SCC.
The frozen protocol is
`PUBLISHED_PEEPS_FULL_MONTH_CROP_SCREEN_PROTOCOL_20260917.md`.

The verified source is all twelve PEEPS v1.1 MPI-ESM1-2-HR SSP5-8.5
monthly `pr` linear coefficients (whole author archive MD5
`eed1a0e8a43bf915c78ec68d0f37e357`), paired to the author's own
absolute annual GMST. MIRCA2000 positive rainfed-maize centers were mapped
to nearest MPI native cells. There are 30,821 positive-area centers,
10,167 touched MPI cells, 2,541 excluded zero-area rows, and
108,086,337.428 ha in the mapped proxy. This is **not** conservative
regridding and does not yet use planting/harvest calendars.

| Author year | Absolute GMST (K) | Mapped rainfed-maize area with at least one negative predicted month |
| --- | ---: | ---: |
| 2015 | 288.1925 | 2.8561% |
| 2030 | 288.6154 | 0.3223% |
| 2050 | 289.1088 | 0% |
| 2100 | 291.3734 | 9.8791% |

The full month-by-month area and negative minima are in the ignored
`data/interim/peeps_author_mpi_ssp585_monthly_20260917/full_month_crop_screen.json`.
No negative value was clipped or imputed. The nonmonotone invalid area is
possible because location/month slopes have both signs; it is **not** a
claim about actual future aridity or crop damage.

On the **fixed 88.266% of rainfed-maize area** with twelve nonnegative
predictions and positive annual totals in both 2015 and 2100, the
area-weighted mean *calendar-year predicted* total changes from 1110.13
to 1153.74 mm (+43.61 mm, +3.93%). The area-weighted mean per-cell
total-variation distance between twelve-month rainfall shares is 0.08739.
These restricted-support descriptive outputs show that the imported
published response can represent **both quantity and monthly allocation**.
They are not global crop-season effects; excluded locations must not be
treated as zero impacts, and within-month dry spells/extremes are absent.

The worker completed with sampled peak group RSS 182,288,384 B and 17,513
B new owned output; free disk remained about 133 GiB. An independently
written audit re-decoded all twelve source files, remapped every center
without the production mapper, and passed all 48 month-year negative-area
and minimum checks, four any-negative-month area checks, and common-support
amount/share checks. Audit peak RSS was 176,193,536 B. Logs, numerical
products and monitor receipts remain ignored under the same interim folder.

**Decision for the pipeline:** the raw published *linear levels cannot be
promoted* as physically valid crop rainfall under this SSP; nearly one
tenth of mapped rainfed-maize area has a negative month in 2100. Retain
them as a transparent published benchmark. Next compare a nonnegative
published formulation (e.g. MESMER-M-TP, if calibrated parameters can be
obtained) or published *changes* anchored to source-matched positive
historical rainfall, against direct same-model climate on crop-calendar
support. Do not silently clip the PEEPS levels. The source model and
scenario here alone cannot establish cross-model global SCC uncertainty.

Primary source: Kravitz and Snyder (2023),
https://doi.org/10.1371/journal.pclm.0000159 ; published coefficient archive,
https://doi.org/10.5281/zenodo.7557622 . MIRCA2000 provenance and license
are in the project's existing source manifest.

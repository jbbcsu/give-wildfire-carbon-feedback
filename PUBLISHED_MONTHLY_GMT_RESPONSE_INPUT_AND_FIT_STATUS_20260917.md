# Monthly GMT–rainfall benchmark: sources and training fit, not yet validated

The project now has a compact, reproducible raw-CMIP6 test of the published
PEEPS-style global monthly pattern-scaling approach. This is a **secondary
climate benchmark**. It is neither the project's primary daily ISIMIP3b
driver nor an agricultural damage or SCC estimate. The registered design and
fixed scenario/time holdouts are in
`PUBLISHED_MONTHLY_GMT_RESPONSE_BENCHMARK_PROTOCOL_20260917.md`.

Exact public `fx/areacella` sources for GFDL-ESM4 `gr1` and IPSL-CM6A-LR
`gr`, both `r1i1p1f1`, were acquired in bounded form. Source metadata,
license, model/member/grid/units, GCS MD5, array hashes, positive finite
areas and matching climate coordinates passed. Their area totals are
510.064 and 510.104 trillion m², respectively. Coordinate matching uses
fixed `atol=1e-10` degree, `rtol=0` after an exact-bit failure showed
only `7.11e-15`/`5.68e-14` degree GFDL lat/lon differences; the failed
receipts/logs remain. Saved area inputs are about 13 KB per model, in
ignored `data/interim`; they are not in Git.

The six raw-CMIP6 monthly temperature stores (two ESMs × historical,
SSP1-2.6, SSP5-8.5) were streamed without retaining large chunks to make
native-cell-area- and calendar-second-weighted annual GMST: 1981–2010
historical and 2015–2100 scenario series. All six source/month/member
identities and server MD5 checks passed. A separate validator recomputed
all **404 annual values** from retained monthly means using 50-digit Decimal
arithmetic; maximum absolute discrepancy was `5.68e-14 K`. Peak sampled
worker RSS was 380.47 MB for GFDL SSP1-2.6; each new owned output was far
below 64 MiB and free disk remained ~134 GiB. The first GFDL SSP5-8.5
attempt stopped at an overly restrictive 96 MiB compressed cap before
decoding its known 107,521,299-byte chunk; a documented 112 MiB cap
passed without relaxing the 512 MiB worker/130 GiB reserve limits.

Using the registered SSP5-8.5 **2015–2080 training period**, per-ESM,
calendar-month, native-grid linear precipitation-versus-annual-GMST
coefficients were fitted for both GFDL and IPSL. A same-training-information
annual-quantity comparator and unchanged historical monthly baseline are
also saved. The fit is centered on each model's 1981–2010 GMST mean; it
never treats the 30-year climatology files as 30 annual observations.
Both real fits passed 130 in-process fixed-sentinel OLS checks each, and an
independent 50-digit Decimal saved-product audit passed all **260**
intercept/slope comparisons. GFDL's sampled fit peak was 469.40 MB, close
to but below the 512 MiB ceiling; IPSL's was 275.27 MB. Their owned outputs
were 18.24 and 7.41 MB. These are algebra/source checks, **not predictive
validation**. The coefficients remain confined to ignored `data/interim`.

Next: run the *predeclared* whole-SSP1-2.6 2031–2060 and late-SSP5-8.5
2081–2100 holdouts without revising fit years or predictors. Compare
monthly model versus quantity-only and no-change baselines for native-grid
monthly amounts, annual totals, month-share redistribution, physical-domain
failures and out-of-training-GMST support. Then transfer the validated
fields to fixed maize calendars/areas and compare crop-season amount and
monthly timing. No daily dry-spell, extreme, heat–moisture covariance,
crop-yield, damage or SCC claim follows from these monthly fits.

Receipts and exact hashes are in
`data/interim/cmip6_*_native_area_20260917/`,
`data/interim/pangeo_*_annual_gmst_20260917/`,
`data/interim/pangeo_annual_gmst_validation_20260917/`,
`data/interim/pangeo_*_ssp585_monthly_pattern_fit_20260917/`, and
`data/interim/pangeo_monthly_pattern_fit_validation_20260917/`.
Reproduction scripts and synthetic tests are in `scripts/` with matching
`acquire_cmip6_native_cell_area`, `build_pangeo_annual_gmst`, and
`fit_pangeo_monthly_pattern` names plus their guarded continuations and
independent validators. Licenses: GFDL CC-BY-SA 4.0; IPSL CC-BY-NC-SA
4.0, with producer acknowledgments. Derived data must not be relicensed
as unrestricted code.

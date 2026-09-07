# Future rainfall basis on fixed irrigation shares

Registered before calculation, September7,2026. Reuse only local derived
season/stage products and fixed MIRCA2000 shares. This is climate-input
construction, not a response fit, historical coefficient export, projected
yield change, causal attribution, welfare estimate or SCC calculation.

Scope: maize and soybean, latitudes39.25/39.75N, harvest2032–2059, the complete
common GFDL/IPSL/MPI by SSP126/370/585 matrix. Omit MRI and UKESM from this
balanced comparison without filling their missing cases. Verify matrix,
realization/member, source config/audit and season/stage hashes. Check weight
bytes against the previously recorded historical allocation hash. Weights
must be fixed2000, crop-season eligible, complete across noirr/firr, sum to1,
and retain the existing definition; no missing cell is filled or renormalized.

Within each regime construct the existing distribution-candidate basis with
the unchanged `build_regime_candidate_basis`. Its input interface requires
outcome fields: explicitly mark every future outcome missing (`NaN`, observed
false); these are not synthetic outcomes and must never enter a regression.
Reuse the existing allocator only as the fixed-exposure arithmetic utility.
Drop missing outcome fields before writing climate-only outputs. Export six
historical direct predictors (log1p seasonal rain, stage1/2 rain shares, maximum
dry spell, Rx5day and three-stage share HHI), stage3share, seasonal rain,
three stage mean temperatures and the weighted zero-rain indicator. Nonlinear
bases are calculated before irrigation-share weighting, never after it.

For each scenario/crop, require both calendar regimes and all28years on the
same supported cell set. Report original calendar cells, excluded cells with
no weights, supported cells, rows, zero-rain flags and actual output bytes.
Compute the Jensen diagnostic log1p(weighted rain) minus weighted log1p(rain),
which should be nonnegative within floating-point tolerance. This is a
calculation-order diagnostic, not a damage estimate.

Pair candidate SSP370/585 against SSP126 within the same model/member/crop,
on exact grid-year keys. Average annual feature differences within cell,
then equally across cells; these are not global area/value-weighted estimates.
For share/HHI contrasts, exclude any cell with a positive-weight zero-rain
regime-year in either path; keep quantities on all supported cells. Report
excluded counts and all model results, not just an ensemble median. Three
stage boundaries remain0/0.3/0.7/1; share HHI is not daily concentration.
Calendar irrigation labels are exposure windows, not separate observed yields.

Synthetic tests must show exact agreement with direct weighted algebra,
Jensen's inequality, failure on duplicate/missing regime keys and mismatched
scenario support, correct shape exclusions and no outcome export. All
existing historical implementations remain unchanged. One monitored process,
numeric threads1, at most1GiB sampled group RSS and64MiB additional disk;
stream one crop/scenario construction at a time. Stop on validation failures,
preserve receipts and disclose amendments. No new raw acquisition.

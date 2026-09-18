# Frozen source-matched rainfall-change diagnostic

Registered before calculating the change scores on September 18, 2026.
This is a **post-level-result diagnostic**, not a new holdout: published PEEPS
and the direct MPI SSP5-8.5 fields share source-model/scenario information.
The purpose is to separate the published pattern's skill at representing
*total* rainfall change from its skill at representing the *distribution
among months*. It does not repair negative predicted rainfall levels.

## Input and support

Use only `data/interim/peeps_mpi_source_reconstruction_20260917/
source_vs_published_crop_center_mm.npz`, SHA-256
`f1556e24ad9e843f064c095474b0d89954ed621d91cc51f006e63b65cb87b08d`.
Its companion result JSON has SHA-256
`f5aeaef121ef712522f6ad4ada66acab4f060e5d60e57bdaf5b479c33b7727fa`.
Inputs are the saved 2015 and 2100 twelve-month **direct two-member mean**
and raw published PEEPS monthly rainfall, on unchanged 30,821 MIRCA2000
rainfed-maize nearest-center points and positive-area weights. Retain all
centers, including locations with negative published monthly *levels*.
Verify shape, finite values, nonnegative direct rainfall, positive weights,
and exact source hashes. No fit, imputation, clipping, scaling or
post-outcome selection is permitted.

## Fixed calculations

At each center and month, calculate direct and published changes as
`2100 minus 2015` in mm. At each center, sum twelve monthly changes to
obtain the annual change. With fixed area weights, report:

1. Direct and published area-weighted mean annual changes; their bias;
   spatial annual-change RMSE and MAE; and fraction of area where their
   annual-change signs agree (zero matches zero only).
2. For each month, the direct and published area-weighted mean monthly
   change, mean-error bias, and spatial RMSE.
3. Define each center's *redistribution component* as its monthly change
   minus one-twelfth of its annual change. Report the weighted root mean
   square difference of these 12-component vectors (equal month weighting)
   and, separately, the weighted root mean square of the annual-change
   error divided by 12. The square of overall weighted monthly-change RMSE
   must equal the sum of the squares of these two orthogonal components
   within numerical tolerance. These components describe changes in
   calendar-month amounts, **not** month shares or crop-year stage exposure.

Independently recompute all reported scalars from the saved arrays with
`math.fsum`, including the decomposition identity. A finite/shape/source
failure is a stop. Run once under the 512 MiB RSS / 64 MiB new-output /
130 GiB free-disk gates; keep receipt and errors. This is an in-sample
climate-input diagnostic only. No yield, agricultural damage, climate
attribution, or GIVE SCC claim is authorized.

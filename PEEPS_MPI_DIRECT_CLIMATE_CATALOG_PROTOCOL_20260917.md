# Preregistered same-source MPI direct-climate catalog discovery

The author PEEPS monthly patterns are model/scenario/member-aggregated and
their raw linear rainfall levels fail the rainfed-maize positivity screen.
Before constructing any source-matched positive rainfall anchor or claiming
an independent direct-climate comparison, inspect the **authors' frozen
CMIP6 Pangeo catalog** at source commit
`d4ed4c479f5399015708135558daa382bbbc2da0`. Stream
`pangeo_table.csv` without saving it. Require its known 22,939,452-byte
length and Git-blob SHA-1
`c1ce147ecdd0eac37648a4b0473f1589bf411c1f`; separately record
SHA-256. Select only exact `MPI-ESM1-2-HR` historical/SSP5-8.5 `pr`/`tas`
`Amon` rows. Retain every declared ensemble member and grid for these
keys, but no climate payload. Report counts/member sets per experiment,
variable and grid, plus each selected `gs://cmip6/` store identity.

Do not assume one selected member equals PEEPS `ensemble_avg`; identify
the relevant averaging/member contract from the pinned source code before
any comparison. Do not infer native-grid equivalence to ISIMIP bias-adjusted
data. Run one bounded worker (sampled RSS <=512 MiB, owned output <=64 MiB,
free disk >=130 GiB, log <=2 MiB). Any catalog-source drift or missing
selection fails closed. This is metadata discovery, not a climate/yield/SCC
result.

Source: Kravitz and Snyder (2023),
https://doi.org/10.1371/journal.pclm.0000159 ; archived code and data
catalog at https://github.com/JGCRI/linear_pattern_scaling .

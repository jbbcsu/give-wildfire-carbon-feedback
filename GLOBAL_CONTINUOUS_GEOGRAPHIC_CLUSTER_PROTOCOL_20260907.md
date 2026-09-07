# Exploratory geographic validation and source-cluster uncertainty audit

This audit extends the frozen continuous maize/soy temporal benchmark without
changing its candidate families, common-support rule, endpoints, or feature
bases. It uses only the retained, assembly-hash-verified 1982--2016 direct,
heat, and historical-scPDSI candidate tables. It neither acquires data nor
rebuilds climate features.

Inner-join the three candidate families on exact crop, latitude, longitude,
and harvest-year keys. Require identical positive observed yield and finite
registered features. Form consecutive-year log-yield changes within exact
source grid cells. Training differences end in 1983--2010; terminal test
differences end in 2012--2016; differences ending in 2011 are excluded so
train and test do not share a yield-level endpoint. As in the parent temporal
benchmark, a terminal source grid cell must have at least one 1983--2010
consecutive difference; this is an availability gate only, not an outcome-
magnitude screen.

Assign every 10-degree latitude-by-longitude source block to one of five folds
before reading outcomes. Latitude block is `floor((lat + 90) / 10)`, longitude
block is `floor(lon_360 / 10)`, and fold is
`(37 * latitude_block + 17 * longitude_block + 20260907) mod 5`. For each
fold, train only on 1983--2010 differences from the other four folds and score
only 2012--2016 differences in the held-out fold. A source grid cell can never
appear in both training and test for the same fold. Require at least two
nonempty held-out 10-degree blocks per fold and at least ten per crop.

Retain the temporal benchmark's five specifications: heat controls alone;
seasonal rainfall quantity; rainfall quantity plus registered distribution,
dry-spell, extreme, and concentration terms; seasonal scPDSI; and stage
scPDSI. Moisture families remain mutually exclusive. Fit scale-normalized
cross-products and fail on rank deficiency or condition number above `1e10`.
Coefficients and row predictions are transient and must not be written.

Report fold and pooled held-out RMSE, with pair counts. For descriptive
source-cluster uncertainty, aggregate squared losses by held-out 10-degree
source block. Within each fold, resample its blocks with replacement using
5,000 PCG64 draws and seed 20260907, retain all pairs within each selected
block, and recompute paired pooled RMSE differences. Report 2.5/50/97.5
percentiles for quantity minus controls, distribution minus quantity,
seasonal scPDSI minus quantity, and stage scPDSI minus quantity. This bootstrap
is conditional on the five fixed fits and treats blocks as descriptive source
clusters; it does not define a random population, correct all spatial
dependence, or supply significance.

Read one Parquet file at a time in 8,192-row batches and nonoverlapping
10-degree latitude blocks. Run the real audit under the bounded process-group
monitor with a 1 GiB sampled-RSS ceiling. The result is aggregate-only and
must remain below 1 MiB. No coefficient export, model promotion, causal
response, climate attribution, future projection, damage, welfare, FAIR, or
SCC use is authorized regardless of the numerical outcome.

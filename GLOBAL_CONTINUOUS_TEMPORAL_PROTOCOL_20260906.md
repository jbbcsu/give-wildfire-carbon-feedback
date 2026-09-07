# Exploratory continuous historical temporal benchmark

Use the retained, assembly-hash-verified 1982–2016 maize and soybean
candidate tables. Inner-join direct weather, heat and scPDSI on exact
crop/grid/year keys, require matching observed positive yields, then retain
only consecutive-year log-yield changes on identical common support.
Training differences end in 1983–2010; terminal differences end in 2012–2016.
Exclude differences ending in 2011 to avoid shared train/test level endpoints.
Score terminal grid cells with at least one training difference only.

All models share differences in three stage mean temperatures and three
crop-specific Tmax degree-day exposures (29 C maize, 30 C soy), intercept,
and deterministic end-year linear/quadratic controls centered at 2000.
Compare controls alone; add difference in log1p seasonal precipitation;
additionally add differences in stage1/2 precipitation shares, longest dry
spell, rx5day and precipitation concentration; or instead add seasonal
scPDSI mean, or three stage scPDSI means. Never stack moisture families.
This is a finite exploratory comparison, not selection or a causal response.

Read selected columns in nonoverlapping 10-degree latitude bands using
8,192-row Parquet batches and retain positive-yield rows. (A first 30-degree
filtered-read attempt exceeded the 1 GiB budget and was terminated before
producing results; the revision changes I/O only, not model/split choices.) Sum
training/test cross-products per model and solve a scale-normalized Gram
system, failing on rank deficiency or condition number above 1e10. Report
test RMSE and R2 relative to training-mean prediction, not coefficients,
row predictions or significance. Test algebra against small direct least
squares. Preserve counts per band and all model outcomes.

Grid-year pairs have equal weights; these are not area/production/welfare
weights or independent observations. GDHY source dependence precludes
treating grid counts as independent evidence. scPDSI full-record calibration
makes this retrospective, not prospective forecasting. The fixed calendar,
irrigation allocation and global transport assumptions are unchanged. No
spatial validation, uncertainty, climate-attribution, welfare or SCC claim.

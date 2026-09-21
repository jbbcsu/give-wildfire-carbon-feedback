# Post-result state-trend sensitivity for the U.S. terminal scores

The prespecified nationwide U.S. benchmark used one common linear yield
trend extrapolated from 1981–2019 into 2020–2025. Its preliminary soybean
pattern improvement was inspected before this sensitivity was registered.
Therefore this is **post-result robustness**, not an independent holdout or
a replacement primary specification selected without outcome information.

Hold fixed the previously validated 2017 <=10%-irrigated-share NASS/
NOAA county-average panel, crop-specific historical/terminal years, county
intercepts, rainfall/temperature/pattern columns, exact terminal support,
and predictive metrics. Replace the single `(year−2000)/10` column with one
such linear slope column for each state represented in 1981–2019 training;
do not also include the common trend, which would be collinear. No state,
term, threshold, window or model family may be selected by the terminal
score. Fit the same unpenalized within-county least squares with rank,
condition and residual-orthogonality checks. A state slope that has no
historical time variation is an explicit failure, not an imputed trend.

Score all three unchanged model families on identical 2020–2025 county-
years and report each crop's RMSE/MAE/bias, annual RMSE, historical blocked
1981–2010-fit/2012–2019 diagnostic (purging 2011), support counts, and
conditional paired state-bootstrap RMSE differences. Interpret any gain as
predictive only. Compared with a single common trend, state slopes may
absorb persistent regional changes, but also raise variance and extrapolate
noisily; report both directions. Do not infer a climate-caused precipitation
effect, directly observed rainfed yields, global transfer, damages or SCC.

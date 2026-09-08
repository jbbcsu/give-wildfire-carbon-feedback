# Historical range check for the real two-crop heat pilot

Registered before calculation, September 8, 2026 UTC. Compare the six newly
available stage Tmax29°C day-count/degree-day fields with cell-specific
1982–2010 historical heat-basis minima/maxima. Stream historical Parquet in
8192-row batches, select only 39.25/39.75N and positive observed yield rows;
require finite features, unique crop/grid/year keys, and at least two years
per cell. Bind historical assembly and new future product hashes. Report all
six features independently, missing-range counts and any-feature-outside on
common evaluable rows. Fixed absolute boundary tolerance 1e-10; no trimming,
pass threshold, parameter fitting, yield response or damage calculation.

This compares the existing historical climate representation with the
GFDL-ESM4 SSP126 2042–2049 pilot, not matched forced/counterfactual climate
paths. Range departures can reflect source differences as well as climate
change. A 29°C soybean check is a sensitivity/input diagnostic, not the locked
30°C soybean response-control specification. It cannot replace that control.
Inside six marginal ranges is not joint support or causal transport validation.
Missing historical-yield cells remain missing, never inferred from neighbors.

Use one monitored process, 1 GiB sampled RAM cap, original approved 64 MiB
combined pilot/extension disk budget. Output one small aggregate receipt only.

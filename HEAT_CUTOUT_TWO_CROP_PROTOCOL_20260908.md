# Same-file two-crop heat/rainfall input join

Registered before this calculation on September 8, 2026 UTC. The user approved
the single 12.3 MiB cutout download with 64 MiB total additional disk use.
The initial maize/noirr pipeline passed on real data. Reuse that file and its
finished products without another download or reconstructing completed heat.

Build only missing maize/firr and soybean/noirr/firr heat, harvest 2042–2049,
29°C threshold and the existing 0/0.3/0.7/1 fractional windows. Verify resident
calendar hashes against the existing manifest. Sequential children, one numeric
thread, 1 GiB sampled RAM cap. Count original acquisition plus new outputs
against the same 64 MiB disk ceiling; preserve failure files, no automatic retry.

Use the existing historical heat-basis validation and allocation functions:
require exact calendar identities, stage lengths, complete keys, threshold sums
and seasonal/stage means before weighting each regime with fixed MIRCA2000
shares. Missing-weight cells remain excluded exactly as in the existing future
rainfall basis; do not renormalize incomplete calendar coverage. Match resulting
keys and stage mean temperatures to the retained GFDL-ESM4/r1i1p1f1 SSP126
rainfall basis, then append six stage heat fields. No outcomes are supplied;
NaN/false placeholders exist only for the shared data-contract API and are
removed from the exported climate table.

Report hashes, rows, scope, resource use and numerical reconciliation. This is
one scenario/decade, two latitude rows, two crops—not a global projection,
response estimate, climate contrast, irrigation benefit, welfare result or SCC.
Other scenarios/models, historical joint support, transport, CO2/adaptation,
economic aggregation and marginal-emissions paths remain unfinished.

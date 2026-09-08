# Independent-model check, registered before IPSL acquisition/calculation

Repeat the completed GFDL matched-scenario diagnostic with IPSL-CM6A-LR,
using its officially verifiedr1i1p1f1 member, W5E5 adjustment, version20210512,
2041–2050daily Tmax files and SSP126/SSP585. Keep geography39.25/39.75N,
crop years2042–2049, calendars, fixed MIRCA2000 weights and maize29°C/soy30°C
thresholds unchanged. New configs bind actual public CC0 source identifiers,
checksums and DOI10.48364/ISIMIP.842396.1. No relabeling of GFDL outputs.

Generalize the wrapper with an explicit model/member identity check tested
against wrong-model/member/scenario/variable/bias-adjustment/frequency input.
Pair exact keys and hash-identical calendars/weights. Existing baseline
behavior is unchanged. Do not rerun GFDL calculations. Compare the same
equal-cell climate summaries; dispersion is not a confidence interval.
Report disagreement or reversed signs plainly; do not select favorable models.

One acquisition/analysis job at a time, one numerical thread, <=1GiB sampled
RAM, <=64MiB additional data per scenario acquisition/processing batch and
>=130GiB free. No full global raw files or per-file permission requests.
Retain both small raw cutouts and provenance. This is a two-model pilot, not
an uncertainty distribution or global agricultural-damage estimate. Historical
response transport, climate attribution, welfare and SCC remain separate.

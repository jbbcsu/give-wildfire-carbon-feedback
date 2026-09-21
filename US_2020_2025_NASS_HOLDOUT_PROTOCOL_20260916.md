# U.S. 2020–2025 county-outcome extension: acquisition and support gate

This is an **outcome acquisition and key-only support stage**, not a fitted
crop response or a climate damage. The direct `IRRIGATED`/`NON-IRRIGATED`
survey series already present locally has only 2–3 county-labeled records per
crop/practice/year in a preliminary 2020–2025 count screen. The formal
post-2019 check will distinguish real FIPS counties, aggregate county codes,
suppressed values and true two-practice pairs before concluding whether a
direct-practice terminal test is feasible. These preliminary counts were
observed before this protocol; no 2020–2025 yield magnitudes were read.

The separately designated alternative is the official USDA NASS Quick Stats
**all-production-practices** annual county yield for corn grain and soybeans,
2020–2025 inclusive. It is not a rainfed or irrigated-specific yield. Exact
filters: `SURVEY`, `CROPS`, `YIELD`, `COUNTY`, `ANNUAL`, `YEAR`, `TOTAL`,
`ALL PRODUCTION PRACTICES`, `BU / ACRE`; corn utilization `GRAIN` and soybean
utilization `ALL UTILIZATION PRACTICES`. Query each crop-year separately via
the existing credential-safe count/data routine, require official count <=
50,000 and exact returned series and row count; preserve reported suppression
and `load_time` fields. Keep raw JSON and key-free SHA-512 manifest in a new
ignored `data/interim/nass_terminal_2020_2025_20260916/source/` directory,
without overwriting the 2018–2022 archived snapshot. Do not expose the API
key. [USDA Quick Stats](https://www.nass.usda.gov/Quick_Stats/) identifies
the database and API as official published agricultural estimates.

Before reading outcome magnitudes, report per-year returned rows, valid FIPS
county rows, suppressed/nonpositive/positive availability categories, exact
county/year duplicates, 2017 crop-specific <=10% irrigated-area selector
coverage (20/30% sensitivities), 2022 selector sensitivity, and overlap with
the existing fixed 419-county direct-weather geography. Suppressed/missing
irrigation shares are unknown, not zero. Any later first-difference test must
require consecutive actual outcome years and no overlapping training/test
level endpoints. A future validation would train only on <=2019 outcomes and
score 2020–2025 without selecting the model by these terminal outcomes.
The period is new for the reported fits, not an untouched confirmatory test
of all research choices (earlier model families/holdouts were inspected).

Weather must be NOAA nClimGrid-Daily from a consistent spatial estimator in
training and terminal periods; existing 2019 county-polygon weights and fixed
2010 crop calendars are the baseline option. A newer NOAA input may revise
old values, and acquisition alone does not establish estimator/temporal
parity. 2020–2025 daily heat, total rain, timing and drought features are not
assumed present. Do not run a yield response or call it rainfed until actual
support, weather provenance, spatial coverage and a separately fixed
estimation/validation contract pass. Even a good held-out score would remain
predictive, not an identified anthropogenic precipitation damage or SCC.

One network/data worker at a time, 512 MiB sampled RSS, <=64 MiB new owned
output per job, >=130 GiB free-disk floor. No wildfire files are touched.

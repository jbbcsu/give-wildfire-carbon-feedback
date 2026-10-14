# Williams wildfire-smoke reproduction admission gate

## Status

The current local package is **rejected**. The investigator-supplied draft
receipt and extracted draft text are hash-bound, but zero of eight operational
artifact groups are present and independently validated. The reported
$50/tCO2 mean, conditional $18.5-$102.6 interval, and $25.91/tCO2 leave-CESM-
out mean remain unpublished external claims. They are not calibration targets,
local reproductions, or additive GIVE values.

The gate reads no file from the separate wildfire-CO2 project. It covers only
wildfire-smoke PM2.5 mortality.

## Required package

Admission for reproduction requires all eight hash-bound validation receipts:

1. A unique 43-simulation inventory with the draft's 36 Park, five Pierce, and
   two Zhao observations, five model labels, fixed 2000-2010 population, source
   hashes, and source-specific regridding metadata.
2. Finite coefficient and standard-error output for 174 estimated countries,
   an explicit global fallback, and a complete mapping to 184 GIVE countries
   under the country-by-model fixed-effect/common-slope specification.
3. Hash-bound baseline mortality and 2020-dollar VSL inputs, the stated
   concentration-response mean 0.008 and standard error 0.00128, full
   country-year support, and an authoritative horizon resolution.
4. Matched annual baseline and 2025 CO2-pulse paths with unique pair/draw IDs,
   declared pulse magnitude and gas units, and no wildfire-carbon feedback.
5. Ten-thousand finite trial outputs, unique IDs, an independently recomputed
   summary, the conditional-interval label, and an explicit no-calibration
   check.
6. All-model plus five leave-one-model-out coefficient and SCC trial outputs,
   with paired draws and independent reaggregation.
7. Hashes, code/environment provenance, license or permission, redistribution
   status for every input, and compliance with the draft's distribution limit.
8. A mortality-overlap boundary excluding wildfire CO2, non-wildfire PM2.5,
   and ozone and resolving existing temperature-mortality and fisheries-
   nutrition mortality so every death and VSL is valued once.

An admitted package only permits a reproduction attempt. It does not establish
the draft result, authorize GIVE transfer, or authorize an SCC addition.

## Unresolved source conflicts

The extracted draft's Figure 2 says 100 Monte Carlo simulations; the requested
production reproduction contract calls for 10,000. The prose also describes
“275 years” while stating 2025 through 2300, which is 276 inclusive years.
Neither ambiguity is resolved by the local draft receipt. A future candidate
must bind an authoritative declaration for both choices; the validator does
not select one post hoc.

## Execution

Run the local rejection audit and synthetic contract tests with:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_williams_wildfire_smoke_admission.py
PYTHONDONTWRITEBYTECODE=1 python3 test/test_williams_wildfire_smoke_admission.py
```

The production candidate manifest path is
`data/raw/williams_wildfire_smoke/artifact_manifest.json`. Raw and licensed
artifacts remain ignored. Group receipts must bind every underlying artifact by
path, byte size, and SHA-256.

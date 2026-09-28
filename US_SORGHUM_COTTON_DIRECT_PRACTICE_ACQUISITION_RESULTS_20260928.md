# U.S. sorghum and upland-cotton direct-practice acquisition results

## Result

The exact NASS records confirm usable historical paired-practice outcome
support for both crops, but recent sorghum support is thin.

| Crop | Raw records | Eligible coded positive records | Paired county-years | Counties | States | Years | Annual pair range |
|---|---:|---:|---:|---:|---:|---:|---:|
| Sorghum grain | 18,144 | 16,475 | 5,270 | 374 | 6 | 1981--2018 | 3--299 |
| Upland cotton | 11,042 | 9,724 | 3,501 | 193 | 6 | 1981--2018 | 17--128 |

These are actual same-county/year pairs, not the earlier marginal-count upper
bounds of 6,439 and 4,524. Sorghum falls from 111 pairs in 2007 to 18 in 2008
and only 3--29 per year thereafter, ending with 8 in 2018. Cotton is more
stable but also declines, with 17--66 pairs per year after 2008. Both are
regional six-state panels rather than nationally representative samples.

All 152 crop--practice--year requests were hash-validated and independently
reparsed. The validator exactly reconstructs all 8,771 paired county-years and
17,542 long practice rows from 29,186 raw API records, verifies the series and
geography/value rules, and confirms that the NASS API key appears in none of
the tracked receipts. Raw records remain ignored.

## Consequence

Sorghum and cotton can support additional historical U.S. validation, but not
yet estimation. Crop-specific planting/harvest calendars, county geography,
daily weather/PDSI coverage, predeclared moisture-family comparisons, and
independent temporal/geographic holdouts are still required. Sorghum's sparse
recent support makes a strong terminal validation unlikely without broadening
the outcome definition, which is not authorized here.

No causal irrigation effect, climate response, national damage, or SCC is
estimated.

## Artifacts

- Protocol: `US_SORGHUM_COTTON_DIRECT_PRACTICE_ACQUISITION_PROTOCOL_20260928.md`
- Acquisition: `us_county_validation/scripts/acquire_nass_sorghum_cotton_direct_practice.py`
- Panel builder: `us_county_validation/scripts/build_nass_sorghum_cotton_direct_practice_panel.py`
- Validator: `us_county_validation/scripts/validate_nass_sorghum_cotton_direct_practice_panel.py`
- Credential-free acquisition receipt:
  `data/provenance/nass_sorghum_cotton_direct_practice_acquisition_20260928.json`
- Panel receipt: `data/provenance/nass_sorghum_cotton_direct_practice_panel_20260928.json`
- Validation: `data/provenance/nass_sorghum_cotton_direct_practice_validation_20260928.json`
- Raw JSON and paired panel remain ignored under `data/raw/` and `data/interim/`.

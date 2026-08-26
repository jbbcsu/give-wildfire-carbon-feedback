# MapSPAM--FAOSTAT welfare-weight input plan

## Recommendation and current gate

Use MapSPAM 2000 v3.0.7 production as a **modeled fixed spatial allocation**
for maize and soybean, and FAOSTAT gross production value as a **national
crop-value control total**. Do not use MapSPAM as an observed outcome or
independent validation source, and do not use FAOSTAT as independent GDHY
validation because GDHY is calibrated to FAO statistics.

For a country (k), crop (c), and MapSPAM cell (g), the proposed fixed
baseline value weight is

\[
w_{g c} = \bar V_{k c,1999:2001}
           \frac{P^{SPAM}_{g c}}
                {\sum_{h\in k}P^{SPAM}_{h c}},
\]

where \(\bar V\) is the mean FAOSTAT gross production value in constant
2014--2016 USD over 1999--2001, and \(P^{SPAM}\) is modeled crop production.
This preserves each available national crop-value total while using SPAM only
for within-country spatial allocation. It does not yet specify future crop
quantity/value growth, agricultural market feedback, or adaptation; each must
enter once in the later welfare layer.

The input and extraction steps are now reproducible, but this formula is **not
yet authorized for estimation or SCC aggregation**. An authoritative
NGA-GEC/GENC audit now resolves the country identity of every four-character
MapSPAM code. Some mapped countries still lack the selected FAOSTAT baseline
value, and `TWN` lacks a current-UN M49 route; neither is imputed or
renormalized away.

## Acquired and verified inputs

### MapSPAM 2000 v3.0.7

- Official archival dataset: IFPRI, *Global Spatially-Disaggregated Crop
  Production Statistics Data for 2000 Version 3.0.7*,
  <https://doi.org/10.7910/DVN/A50I2T>.
- Selected archive: Dataverse datafile 3666788,
  `spam2000v3.0.7_global_production.dbf-csv.zip`, 99,610,984 bytes, official
  MD5 `1dff3f23e222b0648ab609ca5a5f05a5`, plus a locally pinned SHA-512.
- The streaming extractor retains only maize and soybean totals and the four
  systems (rainfed high input, rainfed low input, irrigated, and rainfed
  subsistence), coordinates, source codes, and source-vintage fields. Raw and
  reduced tables remain ignored.
- SPAM is a cross-entropy allocation model using coarser production statistics
  and ancillary inputs. Its gridded production is modeled, not a direct census
  measurement.

The real archive audit found 792,333 production rows and 601,130 cells with
positive maize or soybean. Modeled totals are 637.152 million tonnes of maize
and 160.732 million tonnes of soybean. Aggregate crop totals reconcile to the
four systems within at most 0.4 tonnes for maize and 0.2 tonnes for soybean,
consistent with small archival rounding discrepancies.

The archive is not perfectly described by its codebook:

- 66,350 source rows have a `stat_code` that is not shaped as a three-letter
  ISO3 code; these are preserved verbatim. In the maize/soybean reduced table,
  all 49,222 such rows have four-character legacy FIPS/GEC administrative
  codes whose country prefixes are source-resolved in the separate NGA audit.
- 91 rows have a blank unit, although the file member and `rec_type=R`
  identify production. They contain 703.8 tonnes of selected maize production
  and no soybean production.
- 6,373 rows have a blank source, and 10,015 rows use source `N/F` despite the
  codebook statement that source is always `F`.
- Most rows use `avg(99-01)`, but 10,015 rows use the truncated archival label
  `2006&avg(200` and 5,100 use `avg2004 2006`. These later-vintage groups
  contain 9.716 million tonnes of maize (1.52% of the SPAM maize total) and
  0.476 million tonnes of soybean (0.30%).

These are source facts to model or test, not defects to silently repair.

### FAOSTAT Value of Agricultural Production

- Official catalog: *Value of agricultural production (Global, National -
  Annual)*, <https://data.fao.org/catalog/dataset/b1a04191-c86f-4972-a9d7-28b23568deba>.
- Catalog revision: 2025-01-31; stated coverage through 2024; annual
  maintenance; CC BY 4.0 subject to FAO Statistical Database Terms of Use.
- Bounded official queries acquire item 56, `Maize (corn)`, and item 236,
  `Soya beans`, only. The exact query SQL, schema, response bytes, and SHA-512
  digests are pinned in `data/provenance/faostat_qv_maize_soy.toml`.
- The two frozen responses contain 9,522 maize rows (176 M49 areas) and 4,856
  soybean rows (114 M49 areas), 1961--2024.
- In 1999--2001, constant-2014--2016 USD values are nonmissing for 379 maize
  area-years across 127 M49 areas and 222 soybean area-years across 75 areas.
  Every nonmissing constant-USD observation in the full frozen responses is
  flagged `Estimated value`; those flags remain part of the input.

FAOSTAT values are national annual farm-gate values calculated from production
and producer-price data. They do not supply within-country spatial weights.

### UN M49 crosswalk

The current M49-to-ISO3 mapping is parsed only from the official United Nations
Statistics Division M49 country page. Its raw page and exact digest are pinned;
no explicit data license was identified, so the record uses `NOASSERTION` and
the derived crosswalk is not distributed.

## Exact-only and source-resolved coverage

The original conservative audit matches only a MapSPAM `stat_code` that is an
exact current UN ISO3 code and has at least one nonmissing 1999--2001 FAOSTAT
constant-USD value. It remains a useful no-crosswalk benchmark:

| Coverage bucket | Maize SPAM production | Soybean SPAM production |
|---|---:|---:|
| Exact current ISO3 + FAOSTAT baseline value | 94.279% | 98.630% |
| Current ISO3, no FAOSTAT baseline value | 1.281% | 0.770% |
| Not a current UN ISO3 code | 4.440% | 0.600% |

The separate source-resolved audit combines four exact checks: NIST's FIPS
`AAXX` semantics, MapSPAM's documented `admin2_fips`, the official NGA
GEC-to-GENC crosswalk, and the current UN M49 table. All 196 four-character
codes across 14 prefixes map to current ISO3 countries, and all 49,222 rows
agree with their `admin2_fips` prefix. The same rule agrees with every one of
550,377 directly checkable three-character MapSPAM rows. This raises production
with both an authoritative country assignment and a baseline value to 98.050%
for maize and 99.058% for soybean. The remaining shares are:

| Remaining bucket | Maize | Soybean |
|---|---:|---:|
| Exact current ISO3, no FAOSTAT baseline value | 1.281% | 0.770% |
| GEC-mapped country, no FAOSTAT baseline value | 0.658% | 0.172% |
| `TWN`, GENC-valid but absent from current UN M49 | 0.012% | 0.0002% |
| Unresolved four-character country code | 0.000% | 0.000% |

The full per-code audit stays ignored and is documented in
`MAPSPAM_CODE_LICENSE_DECISION.md`; no spatial overlay or prefix guess is used.

## Phased implementation

### Directly implementable now

1. Re-run the exact acquisition, archive reduction, FAOSTAT validation, and
   current-ISO coverage audit with the tracked scripts and ignored inputs.
2. Preserve all MapSPAM system columns, source/vintage fields, FAOSTAT value
   flags, and missing cells.
3. Build candidate weights for the exact-match subset only as a diagnostic,
   retaining the full global denominator and an explicit unmatched bucket.
   Do not normalize the subset to one and do not pass it to GIVE.
4. Regrid 5-arc-minute SPAM production to the GIVE/GDHY cell support by mass-
   conserving aggregation after the country-code gate closes. Validate global
   and country/crop mass before and after aggregation.

### Needs source resolution or empirical work

1. Audit why selected rows use later national scaling vintages and test a
   sensitivity excluding those rows/countries. Do not relabel them as 2000.
2. Extend the FAOSTAT baseline window only under a pre-registered missing-data
   rule. Report production-weighted coverage before and after any extension.
3. Compare SPAM national production sums with FAOSTAT physical production as a
   reconciliation check, not as independent validation of SPAM or GDHY.

### Needs a modeling choice

Recommended defaults, pending the above audits, are:

- Primary price/value basis: 1999--2001 mean FAOSTAT constant-2014--2016 USD.
- Missing national value: nearest available observation within five years,
  flagged as imputed; no regional-price fill in the primary specification.
  Region/crop price fills belong only in a named sensitivity.
- Nonstandard MapSPAM country codes: use the audited NGA GEC-to-GENC mapping
  only when the row-level `stat_code` and `admin2_fips` prefixes agree and the
  mapped code is current UN ISO3. No spatial overlay is needed in the primary
  country crosswalk; retain it only as an optional independent validation.
- Later MapSPAM source vintages: retain in the primary fixed SPAM surface but
  report exclusion and alternate-vintage sensitivity because the product is
  explicitly a modeled circa-2000 allocation, not a common-year census.
- Licensing: the selected Dataverse object has CC BY 4.0 terms, while the
  MapSPAM website states CC BY-NC 3.0 for materials downloaded there. Use only
  the pinned Dataverse object, cite its DOI, and keep raw inputs and gridded
  derivatives out of Git pending written IFPRI clarification.

The scripts deliberately stop short of assigning missing values or building
weights. That remaining choice affects global welfare coverage and must be
visible in the Methods and sensitivity design before any agricultural damage
or SCC result is reported.

## Reproduction

```bash
./.venv/bin/python scripts/test_acquire_mapspam2000_production.py
./.venv/bin/python scripts/acquire_mapspam2000_production.py

./.venv/bin/python scripts/test_acquire_faostat_qv_maize_soy.py
./.venv/bin/python scripts/acquire_faostat_qv_maize_soy.py

./.venv/bin/python scripts/test_audit_mapspam_faostat_welfare_crosswalk.py
./.venv/bin/python scripts/audit_mapspam_faostat_welfare_crosswalk.py

./.venv/bin/python scripts/test_audit_mapspam_gec_resolution.py
./.venv/bin/python scripts/audit_mapspam_gec_resolution.py
```

All source data, reduced tables, and JSON audits are ignored. Only scripts,
tests, provenance records, and this plan are tracked.

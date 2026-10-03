# LOCA2 U.S. precipitation and agriculture paper

This directory is a separate U.S. manuscript track. It uses CMIP6-LOCA2 as
high-resolution projection and climate-validation evidence for county crop
responses. It is **not** the global GIVE/ISIMIP forcing pathway, and nothing in
this directory opens a causal-damage or SCC claim gate.

The first stage is outcome blind:

1. audit official USGS and UCSD source versions, licenses, variables, ensemble
   identities, calendars, chunking, and file sizes;
2. freeze model/member/scenario grouping and climate-only validation;
3. run a small cloud-chunk pilot without downloading national NetCDF bundles;
4. validate historical LOCA2 climate features against the existing nClimGrid
   county pipeline on fixed counties and years; and only then
5. request a separate authorization before fitting NASS outcomes.

Raw and derived arrays belong under `data/raw/` and `data/interim/`, which are
ignored. Only small manifests, protocols, tests, and validated aggregate
receipts may be tracked.

## Current entry points

- `LOCA2_SOURCE_AND_DESIGN_PROTOCOL_20261003.md`
- `LOCA2_PILOT_RESULTS_20261003.md`
- `config/loca2_us_design_v1.toml`
- `scripts/audit_official_catalog.py`
- `tests/test_audit_official_catalog.py`
- `manuscript/MAIN_MANUSCRIPT.md`
- `manuscript/METHODS_SUPPORTING_INFORMATION.md`

# Hultgren public-input coverage audit

## Decision

The public materials support exact reproduction of the published historical
maize response, but they do not support exact reconstruction of the upstream
weather pipeline or source spatial aggregation. The project should therefore
keep two distinct routes:

- **source-exact response benchmark:** retain the recovered prepared regression
  dataset, published estimate, calendar rules, and independently reproduced
  coefficients/covariance; and
- **alternative-product transport:** apply the documented feature algebra to
  ISIMIP/GSWP weather and explicit MIRCA or polygon weights, labeling climate
  product and spatial-weight uncertainty rather than calling it replication.

An author request remains worthwhile for the exact GMFD primitives, SAGE
any-crop grid weights, future NEX-GDDP transformed inputs, spatial crosswalk,
and reuse terms.

## Public repository audit

We pinned the authors' [GitLab replication repository](https://gitlab.com/ClimateImpactLab/cil-ag-replication-package)
at commit `3ccdffcd4e4ff6e55566ce76e2aac130ee86349a`. A recursive GitLab API inventory
returned 1,039 entries, including 598 blobs. Filename searches returned six
`gmfd` files, all crop tables; zero `sage`, `anycrop`, `ready`, or license-file
matches. The reviewed historical commit
`dae5fe8d0d4a260328e4baa45b547368bd6790b3` adds the prepared
`corn_gmfd_v1_ready.dta`, which we recovered and used for the exact historical
response reproduction. It does not add primitive daily GMFD or SAGE raster
inputs.

The current 62.5 MB `corn_gmfd_v1.dta` has 433,859 rows and exactly eight
fields: country and administrative identifiers, year, planted area, and
harvested area. Despite its filename, it contains no weather variables. The
4.98 MB `agglomerated-world-new-hierid-crop-weights.csv` has 24,378
administrative rows and crop/all-crop weight columns. It is a downstream
administrative aggregation table, not a grid-cell-to-region weather-weight
file. The public maize shapefile has one dissolved global crop-growing-area
feature with a single `area` field; it is not a set of administrative polygons
or pixel weights.

These checks are hash-bound in
`data/provenance/hultgren_public_input_coverage_audit_20260923.json` and rerun by
`scripts/audit_hultgren_public_input_coverage.py`. Raw files remain ignored and
are not redistributed because no repository license file was found.

## Implication for the precipitation-SCC project

The missing source inputs do not invalidate the published response benchmark.
They prevent us from claiming that GSWP/ISIMIP plus MIRCA reproduces the
paper's GMFD/SAGE climate-input pipeline. This distinction is already visible
in the Iroquois diagnostic: multi-cell spatial weighting improves some rainfall
comparisons, but remaining error cannot be assigned cleanly between climate
product and weights.

The revised unsent request in `HULTGREN_DATA_ACCESS_REQUEST_DRAFT_20260923.md`
now asks only for inputs that are genuinely absent. Sending it remains a user
decision; no message has been sent to the authors.

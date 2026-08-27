# Published Blue-SCC fisheries benchmark audit

## Result

The most important literature gap identified in the initial fisheries plan is
now partly closed. Bastien-Olvera et al., *Accounting for ocean impacts nearly
doubles the social cost of carbon* (doi:10.1038/s41558-025-02533-5), provides
an open repository with country fisheries damage coefficients and SCC source
data. The audited repository is https://github.com/berbastien/blue-scc at
commit `dbc0d8cb21c81f1508abfaf9e5c0f5671ccdd83f`.

The paper's Figure 4 source workbook reports the following 2020 baseline SCC
components (USD per tCO2):

| Component | Published value |
|---|---:|
| Total blue SCC | 48.281363 |
| Fisheries market value | 0.057040 |
| Fisheries non-market use value | 22.040509 |
| Fisheries total | 22.097550 |

Thus fisheries are 45.77% of the published total blue SCC under those settings,
and 99.74% of the fisheries component is the non-market-use/nutrition pathway.
These are external published results, not estimates from the GIVE fisheries
project and not outputs from the local FishMIP scenario benchmark.

The executable workbook audit fails closed if any required 2020 component is
missing, duplicated, nonnumeric, or nonfinite, or if the total is zero. This
prevents an ambiguous spreadsheet row from being silently selected while
leaving all transferability, welfare, matched-pulse, and SCC gates closed.

## What the published implementation does

The market pathway reads Free et al. country profit projections, averages
duplicates by country, management scenario, year, and RCP, and uses RCP2.6 as
the time-varying reference. Under the `Full Adaptation` case it converts profit
differences to percentage points of GDP after applying continent-level direct,
indirect, and induced output multipliers, then fits a zero-intercept country
slope of GDP-fraction change on temperature difference. The released country
coefficient table has 143 finite rows: 122 negative, 18 positive, and 3 zero.

This is a published damage-function benchmark, but it is not a consumer-plus-
producer-surplus calculation. The regional output multipliers also require an
explicit overlap test against other GIVE market damages.

The non-market-use pathway begins with Cheung et al. nutrient-availability
projections for protein, calcium, omega-3, and iron. It combines temperature
slopes with selected nutrient-relative-risk evidence, GBD cause-specific
baseline mortality, country seafood dependence and undernourishment, a fixed
5% no-substitution share, and income-scaled value of statistical life. Because
this pathway dominates the published fisheries SCC, those assumptions—not the
market catch/revenue conversion—are the highest-value replication and
sensitivity targets.

## Compatibility with the current FishMIP work

The two tracks are complementary but cannot be spliced mechanically:

- the local FishMIP benchmark is gridded total-catch density from BOATS and
  EcoOcean under SSP scenarios;
- the published market pathway uses country profit projections from the Free
  et al. bioeconomic model under management/adaptation scenarios; and
- the published nutrition pathway uses separate nutrient-availability
  projections, not FishMIP total catch.

Accordingly, FishMIP remains an independent biophysical sign, forcing, and
model-spread check. The Blue-SCC coefficients become the direct published SCC
benchmark. A future bridge requires either species/nutrient composition and
trade/consumption incidence for FishMIP or a deliberate replication of the
Free et al. and Cheung et al. inputs.

## License and integrity boundary

No explicit root license file was present in the public repository at the
audited commit. The project therefore does not copy its code, country
coefficients, or source workbooks. The local audit script reads a separately
cloned checkout, validates exact hashes and transparent method tokens, and
writes aggregate-only facts. License clarification or a clearly licensed
Zenodo record is required before vendoring or redistributing source artifacts.

The tracked receipt is
[`data/provenance/blue_scc_fisheries_literature_benchmark_20260826.json`](data/provenance/blue_scc_fisheries_literature_benchmark_20260826.json).
It keeps the matched-pulse, welfare, GIVE-damage, and SCC-integration gates
closed.

Reproduce the audit after cloning the exact external commit outside this
repository:

```bash
python3 scripts/audit_blue_scc_fisheries_benchmark.py \
  --source-root /path/to/blue-scc \
  --config config/blue_scc_fisheries_literature_benchmark_v1.toml \
  --out data/provenance/blue_scc_fisheries_literature_benchmark_20260826.json

python3 test/test_blue_scc_fisheries_benchmark.py
```

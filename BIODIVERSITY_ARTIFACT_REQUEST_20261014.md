# Biodiversity nonuse replication artifact request

Status: publication-quality draft only; not sent. The biodiversity component
remains excluded from GIVE.

## Why this request is now the shortest defensible route

The official RFF landing page for Wingenroth et al. (2024) still links the
working-paper PDF but no replication package. The PDF specifies the model and
reports an external literature benchmark of approximately USD 8/tCO2 in 2020
dollars, but does not publish the numerical inputs needed to reproduce its
preferred distribution.

A source-pinned audit of the official `rffscghg/MimiGIVE.jl` `main` branch at
commit `abf0b6feab1ca246cfe41ac205a65d292851c281` (October 6, 2026) found no
tracked UTF-8 file containing the configured biodiversity/nonuse search terms.
That scoped negative result does not prove that no private or differently
named artifact exists. It does establish that the current public repository
cannot supply the missing component. Its present country-to-FUND mapping must
not be substituted for the article mapping without confirmation.

The paper PDF retrieved October 14, 2026 has SHA-256
`c1d92ad56a1508fb02ea8ba094c7bf85152464b640c4297a85fed5b0280e3511`.
The paper's CC BY-NC-ND 4.0 notice is not a license for unreleased code or
data. The exact public-source pins and the seven-part request are machine-bound
in `config/biodiversity_replication_request_v1.json`.

## Draft message to the authors

Subject: Replication artifacts for the GIVE biodiversity nonuse extension

Dear authors,

We are evaluating a biodiversity nonuse-value component for GIVE and would
like to reproduce the preferred specification in Wingenroth et al. (2024)
without inferring coefficients from the reported social-cost benchmark.

Could you point us to a public replication package or provide the seven
artifact groups below? Machine-readable tables and executable source are
preferred. For every file, please provide a version or commit, SHA-256 hash,
and reuse license.

1. The article-generating biodiversity source revision, dependency lockfile,
   random seeds, run instructions, and commands for the preferred and
   comparison specifications.
2. The 16 recalculated FUND-region `beta` values and their complete
   derivation inputs: `eta`, source income and willingness-to-pay values,
   currency, price year, units, formulas, and uncertainty treatment.
3. The updated temperature-response calibration: the 389 grouped Urban input
   values, the three censored all-extinct cases and censor rule, species or
   sample-size weights, the 20,000 `phi` bootstrap draws, seed, and executable
   construction code.
4. The exact article country universe and country-to-FUND-region mapping,
   including the mapping version and treatment of territories or exclusions.
5. The 10,000-run joint uncertainty manifest linking socioeconomic,
   FaIR/climate, `phi`, regional valuation, and discounting draw identifiers,
   including dependence and seed rules.
6. Matched annual baseline and pulse country outputs through the terminal
   year, plus a pulse manifest giving the exact emissions magnitude, unit,
   year, injection convention, and normalization to USD/tCO2. This should
   explicitly link the paper's 0.1-Mt computational pulse to the one-ton
   normalized figure caption and final unit.
7. Checksums, code/data licenses, and an accounting-boundary statement that
   the output contains nonuse/existence value only. Please identify any use
   services included in the implementation, especially agriculture,
   fisheries, aquaculture, reef tourism or recreation, coastal protection,
   carbon-cycle effects, hunting, subsistence, commercial harvest, or other
   market ecosystem services.

For clarity, we will treat the paper's approximately USD 8/tCO2 result only as
an external literature benchmark. We will not calibrate to it, allocate it
across ecosystem services, or add it to GIVE unless the released artifacts
reproduce the preferred distribution and pass the overlap checks below.

Thank you for any guidance or source we may have missed.

[Sender name and affiliation]

## Minimum machine-readable interfaces

The exact required column names are in the JSON contract. At minimum:

- `regional_beta.csv` binds each of the 16 regions to `beta`, `eta`, the
  source income/WTP observations, units, price year, and derivation ID.
- `urban_phi_inputs.csv` preserves study, year, warming, taxon, region,
  species counts, extinction counts, bootstrap weight, and censor status;
  `phi_draws.csv` carries stable draw IDs and the bootstrap seed/method.
- `country_fund_region_map.csv` includes stable country IDs, ISO3 where
  applicable, mapping version, inclusion status, and exclusion reason.
- `joint_draws.csv` binds every Monte Carlo run to all socioeconomic,
  climate, response, valuation, and discount identifiers.
- `annual_country_nonuse.csv` contains matched baseline/pulse rows with all
  state variables and undiscounted 2020-USD annual damage. A separate pulse
  manifest records injection and normalization semantics.

CSV should be UTF-8 with a header row, decimal points rather than locale
formatting, explicit missing values, stable row identifiers, and no merged
cells. JSON metadata should use explicit units and ISO-8601 dates.

## Acceptance and overlap gates

Receipt alone is not acceptance. Before any GIVE result is authorized, an
independent run must reproduce the article's preferred distribution from the
released inputs; reconcile the pulse amount, unit, year, and normalization;
match baseline/pulse keys and fixed socioeconomic inputs; pass zero-pulse and
pre-divergence identities; reconcile country sums to annual global totals;
and verify that the component is inserted and discounted exactly once.

The acceptable welfare boundary is nonuse/existence value only. Crop and
agricultural productivity, fisheries and aquaculture, reef tourism and
recreation, coastal protection, carbon-cycle effects, hunting and
subsistence, commercial harvest, and every other market or use service remain
excluded. No residual may be allocated or renormalized among sectors.

Until all gates pass, the only defensible manuscript presentation is a clearly
labelled published external benchmark, separate from the GIVE total and not a
reproduced estimate.

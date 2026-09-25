# Usage-threshold pause checkpoint

## Verified state

The precipitation branch has a passing preliminary-release gate for the
paired annual-global-maize rainfall-quantity channel. The central
fixed-adaptation, uncapped equal-26-model result at GIVE's 2% Ramsey schedule
is -$0.00610173/tCO2 (2020 USD). The full registered design contains 936 paired
paths and 3,744 SCC values. Its 2% unweighted design percentiles are
-$0.01137 to +$0.00104; these are structural design summaries, not a
probability interval. The central coefficient-only normal interval is
-$0.01037 to -$0.00183.

The newest interpretation checks are exact accounting decompositions of that
narrow result:

- 106 country components reconstruct all 26 climate-model SCCs. Sixty-one
  country means are negative and 45 are positive, but every country component
  changes sign across at least one model. The United States and China account
  for 74.9% of gross absolute components. Removing them as an accounting
  diagnostic leaves -$0.00024980/tCO2.
- At the 2% schedule, 44.1% of the signed value accrues in 2020--2050 and
  27.3% in 2051--2100. The share through 2100 is 60.2%, 71.4%, 80.6%, and
  87.2% under the 1.5%, 2.0%, 2.5%, and 3.0% schedules. All 104
  model-by-schedule totals reconstruct the independent diagnostic. Twenty-five
  models are negative in every post-pulse year and MPI-ESM1-2-LR is positive
  in every post-pulse year; none changes annual sign.
- The coefficient covariance, six fixed/uncapped market cases, Table 3, three
  figures, primary references, manuscript links, README links, claim language,
  tracked-path exclusions, and focused synthetic tests all pass the release
  gate.

The current result remains explicitly incomplete. It holds within-season
rainfall shares fixed and excludes causal drought/timing effects, additional
crops, endogenous irrigation and adaptation costs, trade/storage, and a joint
probability model. It is not the total precipitation-agriculture SCC and must
not be added to MooreAg as a separate sector.

## Parallel tracks

The U.S. NASS evidence supports irrigation stratification and retaining
seasonal quantity as the parsimonious reference. PDSI and within-season
distribution sometimes add predictive value, especially for non-irrigated
corn or soybean, but the improvements are not uniformly stable across periods,
states, temperature controls, and outcome-practice definitions. No U.S.
causal climate-damage coefficient or U.S.-only SCC is authorized.

The fisheries project has no local SCC. The external Blue-SCC benchmark is
$22.09755/tCO2 under its own baseline, but its $22.04051 nutrition/non-market
component and $0.05704 market component cannot be added directly to GIVE.
The nutrition/mortality pathway requires cause-of-death and valuation
reconciliation against Cromar; the market pathway requires consumer/producer
surplus and macro/agriculture overlap reconciliation. FishMIP paths remain
unweighted structural scenarios because the blocked observed-catch prediction
does not support empirical model probabilities.

## Next scientifically decisive steps

1. Freeze a mutually exclusive response design for annual quantity versus
   drought/timing. Do not stack PDSI, SPEI, raw precipitation, and temperature
   coefficients unless a prespecified path decomposition identifies distinct
   contributions.
2. Extend the published-response benchmark beyond maize only when crop-specific
   response, calendar, value, irrigation, and future-climate support can be
   validated under the same accounting contract.
3. For the U.S. analysis, distinguish predictive validation from causal
   identification. A result suitable for SCC transport needs an explicit
   climate counterfactual, stable out-of-sample response, and irrigation-aware
   welfare mapping.
4. For fisheries, first build a matched marginal climate/ocean response for
   each structural FishMIP path. Then value consumer and producer surplus.
   Add a nutrition/mortality residual only after explicit subtraction of the
   relevant GIVE baseline pathway.
5. Keep raw data ignored and continue one memory-bounded worker at a time.
   Do not reacquire the intentionally evicted bulk climate cache unless a
   named downstream calculation requires a checksum-pinned source file.

## Resume and verification

Start from the current precipitation branch and read, in order:

1. `README.md`
2. `PRELIMINARY_RESULTS_AND_CLAIM_BOUNDARIES_20260925.md`
3. `REPRODUCE_PRELIMINARY_SCC_RELEASE_20260925.md`
4. `manuscript/MAIN_MANUSCRIPT.md`
5. `manuscript/METHODS_SUPPORTING_INFORMATION.md`

Re-run the fail-closed bundle check with a fresh output path:

```bash
.venv/bin/python scripts/validate_preliminary_scc_release.py \
  --output data/interim/preliminary_scc_release_validation_resume.json
```

The expected claim gates are: paired quantity-channel SCC `true`; full
precipitation-agriculture SCC `false`; probabilistic total uncertainty
`false`; causal drought/timing SCC `false`. Any attempt to open a closed gate
must be supported by new evidence rather than a relabeling of the present
quantity benchmark.
